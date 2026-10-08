import math
import os
import sys
import threading
import time
import cv2
import numpy as np
import pygame

import cleanup
import loading

CAPTURE_W = 640
CAPTURE_H = 480
DISPLAY_W = 1280
DISPLAY_H = 720
FPS       = 30


MAX_CAMERAS = 8
IDLE_MENU = 60.0        # seconds without the player moving (or nobody there): back to the menu
LEVEL_SHOW = 2.0        # seconds the difficulty is shown after a parent pressed 1 / 2 / 3


def _try_open(index: int):
    """Open camera `index` (DirectShow) and make sure it really delivers frames."""
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if cap.isOpened() and cap.read()[0]:
        return cap
    cap.release()
    return None


def _configure(cap: cv2.VideoCapture) -> None:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAPTURE_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_H)
    cap.set(cv2.CAP_PROP_FPS,          FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)


def open_camera(attempts: int = 8):
    """Returns (capture, index). Looks through all camera numbers, because phone-as-webcam
    apps (DroidCam, ...) and virtual cameras do not sit at index 0. Set the environment
    variable CAMTOY_CAMERA=<number> to force one. The camera can also stay busy for a moment
    after a previous run released it, so the whole search is retried for a few seconds."""
    forced = os.environ.get("CAMTOY_CAMERA", "").strip()
    for _ in range(attempts):
        order = [int(forced)] if forced.isdigit() else range(MAX_CAMERAS)
        for i in order:
            cap = _try_open(i)
            if cap is not None:
                _configure(cap)
                return cap, i
        time.sleep(0.6)
    raise RuntimeError(
        "Webcam wurde nicht gefunden.\n"
        "Bitte prüfen:\n"
        "  Ist die Kamera (oder DroidCam / die Handy-App) verbunden?\n"
        "  Einstellungen → Datenschutz & Sicherheit → Kamera → Desktop-Apps erlauben\n"
        "  Mit der Taste C wechselt man später zwischen mehreren Kameras."
    )


def next_camera(current: int):
    """Opens the next working camera after `current` (wraps around). Returns (cap, index) or None."""
    for step in range(1, MAX_CAMERAS):
        i = (current + step) % MAX_CAMERAS
        cap = _try_open(i)
        if cap is not None:
            _configure(cap)
            return cap, i
    return None


class FrameGrabber:
    """Reads the camera in a background thread so cap.read() blocking
    overlaps with processing/rendering instead of adding to it."""

    def __init__(self, cap: cv2.VideoCapture) -> None:
        self._cap = cap
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._seq = 0
        self.fps = 0.0
        self.size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        self._running = True
        self._pending = None            # a new capture to switch to (handled by the reader thread)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def switch(self, cap: cv2.VideoCapture) -> None:
        """Hands over a new capture; the reader thread swaps it in between two reads."""
        self._pending = cap

    def _run(self) -> None:
        t0, n = time.perf_counter(), 0
        while self._running:
            if self._pending is not None:
                old, self._cap, self._pending = self._cap, self._pending, None
                old.release()
            ret, frame = self._cap.read()
            if ret:
                with self._lock:
                    self._frame = frame
                    self._seq += 1
                n += 1
            now = time.perf_counter()
            if now - t0 >= 1.0:
                self.fps, t0, n = n / (now - t0), now, 0

    def latest(self) -> tuple[int, np.ndarray | None]:
        with self._lock:
            return self._seq, self._frame

    def stop(self) -> None:
        self._running = False
        self._thread.join(timeout=1.0)
        for cap in (self._cap, self._pending):          # give the camera back
            if cap is not None:
                cap.release()


def to_surface(frame_rgb: np.ndarray, size) -> pygame.Surface:
    # OpenCV scales ~5x faster than smoothscale; BGRA is the screen's own pixel layout,
    # so the surface can wrap the array without another conversion
    bgra = cv2.resize(cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGRA), size, interpolation=cv2.INTER_LINEAR)
    return pygame.image.frombuffer(bgra, size, "BGRA")


def cutout_surface(frame_rgb: np.ndarray, mask: np.ndarray, size) -> pygame.Surface:
    h, w = frame_rgb.shape[:2]
    if mask.shape != (h, w):
        raise ValueError("Maske passt nicht zum Bild")
    bgra = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGRA)
    bgra[:, :, 3] = np.clip(mask * (255 / 0.3) - 0.35 * 255 / 0.3, 0, 255)
    return pygame.image.frombuffer(cv2.resize(bgra, size, interpolation=cv2.INTER_LINEAR), size, "BGRA")


def MINIGAME_CLASSES():
    """The games in menu order (imported late: they need pygame to be up)."""
    from minigames.animals import AnimalGame
    from minigames.bubbles import BubbleGame
    from minigames.car import CarGame
    from minigames.dressup import DressUpGame
    from minigames.kungfu_master import KungFuGame
    from minigames.pizza import PizzaGame
    return [KungFuGame, BubbleGame, AnimalGame, DressUpGame, PizzaGame, CarGame]


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(
        (DISPLAY_W, DISPLAY_H),
        # SCALED: logical 1280x720, stretched to the real screen (letterboxed if needed)
        pygame.SCALED | pygame.FULLSCREEN,
        vsync=1,
    )
    pygame.mouse.set_visible(False)
    # exe only: wipe unpack folders that earlier crashed/killed runs left in %TEMP%
    threading.Thread(target=cleanup.remove_stale_temp_dirs, daemon=True).start()
    pygame.display.set_caption("CamToy")
    clock    = pygame.time.Clock()

    # Heavy start-up work runs behind an animated loading screen
    res: dict = {}

    def load_camera() -> None:
        cap, index = open_camera()
        for _ in range(12):          # discard first frames while the camera warms up
            cap.read()
        res["cam_index"] = index
        res["grabber"] = FrameGrabber(cap)

    def load_minigames() -> None:
        from minigames.common import Ctx, Sounds, Speaker
        from posetracker import PoseTracker
        tracker = PoseTracker(res["grabber"], (CAPTURE_W, CAPTURE_H), DISPLAY_W / DISPLAY_H)
        tracker.start()
        from minigames.warmup import prewarm             # polished sprites, made while the model loads
        prewarm(MINIGAME_CLASSES())
        tracker.ready.wait(30)
        if tracker.error:
            raise RuntimeError("Pose-Modell konnte nicht geladen werden.\n" + tracker.error)
        res["tracker"] = tracker
        photos = os.path.join(os.path.expanduser("~"), "Pictures", "CamToy")
        res["ctx"] = Ctx(DISPLAY_W, DISPLAY_H, Sounds(True), Speaker(), tracker, photos)
        from music import MusicPlayer
        res["music"] = MusicPlayer()           # composes the menu / mini-game loops

    err = loading.run(screen, [
        ("Kamera wird geöffnet …",           3, load_camera),
        ("Spiele und Musik werden geladen …", 6, load_minigames),
    ])
    if err is not None:
        if not isinstance(err, RuntimeError):
            raise err
        from minigames.common import text as _text
        screen.fill((40, 20, 30))
        for i, line in enumerate(str(err).split("\n")):
            _text(screen, line, 34, (48, 60 + i * 46),
                  (255, 120, 120) if i == 0 else (255, 255, 255), anchor="midleft")
        pygame.display.flip()
        while True:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.KEYDOWN):
                    pygame.quit()
                    sys.exit(1)

    from menu import Menu
    import gfx
    from minigames.common import draw_cursors, draw_stars_row, ease_out_back, rainbow, text, veil
    from minigames.pose import PlayerPicker, make_players
    import telemetry

    grabber, tracker, ctx = res["grabber"], res["tracker"], res["ctx"]
    cam_index = res["cam_index"]
    jukebox = res["music"]
    tele = telemetry.Telemetry(telemetry.enabled())
    ctx.log = tele.event
    tele.event("camera", index=cam_index, size="%dx%d" % grabber.size)

    MINIGAMES = MINIGAME_CLASSES()
    menu = Menu(ctx, [(g.title, g.icon) for g in MINIGAMES])

    last_time = time.perf_counter()
    last_fid  = -1
    cam_surf = person_surf = cam_small = person_small = None
    mini = None

    MINI_TRACKS = ["master", "bubbles", "animals", "dressup", "pizza", "car"]
    pending, count_t, count_n = 0, 0.0, 3   # picked menu entry + its 3-2-1 countdown
    phase = "menu"               # menu -> countdown -> mini -> menu
    picker = PlayerPicker()      # one child plays; anybody else in view is ignored
    player_slot = None
    last_active, active_at = time.perf_counter(), None   # when the player last moved, and from where
    level_t = -9.0               # when a parent last changed the difficulty

    def goto_menu() -> None:
        nonlocal phase, mini, last_fid, last_active
        last_active = time.perf_counter()
        if mini is not None:
            mini.on_exit()
            mini = None
        ctx.has_mask = False
        tracker.set_segmentation(False)
        tracker.set_active(True)
        jukebox.play("menu")
        menu.pause()
        last_fid = -1
        phase = "menu"
        tele.event("phase", to="menu")

    def begin_countdown(choice: int) -> None:
        """A game was picked with the hands: count 3-2-1, then it starts."""
        nonlocal phase, pending, count_t, count_n
        pending, count_t, count_n = choice, 0.0, 3
        ctx.play("tick")
        phase = "countdown"

    def start_mini(i: int) -> None:
        nonlocal phase, mini, last_active
        last_active = time.perf_counter()
        mini = MINIGAMES[i](ctx)
        tracker.set_active(True)
        jukebox.play(MINI_TRACKS[i])
        phase = "mini"
        tele.event("phase", to="mini", game=MINIGAMES[i].__name__, level=ctx.level)

    goto_menu()

    running = True
    loop_start = time.perf_counter()
    try:
        while running:
            clock.tick(120)   # only idles while waiting for the next camera frame
            now = time.perf_counter()
            loop_ms, loop_start = (now - loop_start) * 1000, now

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        if phase in ("countdown", "mini"):
                            goto_menu()
                        else:
                            running = False
                    elif ev.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                    elif ev.key == pygame.K_c:                # next camera (several webcams / DroidCam)
                        found = next_camera(cam_index)
                        if found:
                            grabber.switch(found[0])
                            cam_index = found[1]
                    elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        ctx.level = ev.key - pygame.K_0
                        level_t = now
                        tele.event("level", level=ctx.level)
                    elif ev.key == pygame.K_m:                # play-test: "look at this moment"
                        tele.mark(screen, phase)
                    elif ev.key == pygame.K_F3:
                        tele.overlay = not tele.overlay

            # ---- menu / games: pose driven, full-frame camera picture ----
            dt = min(now - last_time, 0.1)
            last_time = now
            if tracker.error:
                screen.fill((40, 20, 30))
                text(screen, "Kamera-Fehler: " + str(tracker.error)[:70], 34,
                     (DISPLAY_W // 2, DISPLAY_H // 2))
                pygame.display.flip()
                continue

            fid, frame, people, masks = tracker.latest()
            people = picker.update(people, dt)        # only the child plays (see pose.PlayerPicker)
            if people and people[0][0] != player_slot:
                player_slot = people[0][0]
                last_fid = -1                         # cut out the new player right away
                tele.event("player", slot=player_slot,       # scores: to check the child detection
                           scores=",".join(f"{s}:{v:.2f}" for s, v in sorted(picker.scores.items())))
            mask = masks.get(player_slot) if masks and people else None
            want_mask = bool(mini and mini.needs_mask)
            # A game may show the player smaller, at a fixed spot (scale, left, top as screen
            # fractions), e.g. sitting in a car. The pose is mapped into that picture too.
            view = getattr(mini, "view", None) if phase == "mini" else None
            if frame is not None and fid != last_fid:
                last_fid = fid
                cam_surf = to_surface(frame, (DISPLAY_W, DISPLAY_H))
                person_surf = None
                if want_mask and mask is not None:
                    try:
                        person_surf = cutout_surface(frame, mask, (DISPLAY_W, DISPLAY_H))
                    except Exception:  # noqa: BLE001
                        person_surf = None
                if view:
                    size = (int(DISPLAY_W * view[0]), int(DISPLAY_H * view[0]))
                    cam_small = to_surface(frame, size)
                    person_small = (cutout_surface(frame, mask, size)
                                    if person_surf is not None else None)
            ctx.has_mask = want_mask and person_surf is not None
            if view:
                mapped = []
                for slot, lm in people:
                    lm = lm.copy()
                    lm[:, 0] = view[1] + lm[:, 0] * view[0]
                    lm[:, 1] = view[2] + lm[:, 1] * view[0]
                    mapped.append((slot, lm))
                people = mapped
            pose = make_players(people, DISPLAY_W, DISPLAY_H)

            # nobody there, or a "person" that never moves (a coat, a poster - play-test: a game
            # ran all night): the game goes back to the menu by itself
            pts = pose.pointer_points() if pose else []
            if pts:
                c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), len(pts))
                if active_at is None or c[2] != active_at[2] or math.hypot(c[0] - active_at[0], c[1] - active_at[1]) > 40:
                    active_at, last_active = c, now

            if phase == "mini":
                mini.update(dt, pose)
                if mini.exit or now - last_active > IDLE_MENU:
                    if not mini.exit:
                        tele.event("idle", game=type(mini).__name__)
                    goto_menu()
                    continue
            elif phase == "countdown":
                count_t += dt
                if count_t >= 3.0:
                    start_mini(pending)
                    continue
                if 3 - int(count_t) != count_n:          # a new number appeared
                    count_n = 3 - int(count_t)
                    ctx.play("tick")
            else:
                sel = menu.update(dt, pose)
                if sel is not None:
                    begin_countdown(sel)
                    continue

            if cam_surf:
                screen.blit(cam_surf, (0, 0))
            else:
                screen.fill((60, 80, 120))
            if phase == "mini":
                mini.draw_back(screen, pose)
                if view:
                    where = (int(view[1] * DISPLAY_W), int(view[2] * DISPLAY_H))
                    if ctx.has_mask and person_small is not None:
                        screen.blit(person_small, where)
                    elif cam_small is not None:           # no mask: show the camera window instead
                        screen.blit(cam_small, where)
                elif ctx.has_mask:
                    screen.blit(person_surf, (0, 0))
                mini.draw(screen, pose)
            elif phase == "countdown":
                screen.blit(veil((DISPLAY_W, DISPLAY_H), (20, 25, 70, 110)), (0, 0))
                frac = count_t - int(count_t)               # 0 -> 1 within each second
                mid = (DISPLAY_W // 2, DISPLAY_H // 2 - 10)
                gfx.blit_center(screen, gfx.sunburst(320, rainbow(count_n, 6, .35)), mid, angle=count_t * 30)
                gfx.blit_center(screen, gfx.label(str(count_n), 300, rainbow(count_n, 6, .55)), mid,
                                scale=ease_out_back(frac / 0.35) * (1 - 0.15 * frac))
                draw_cursors(screen, pose, count_t)
            else:
                menu.draw(screen, pose)
            if now - level_t < LEVEL_SHOW:                # for the parent: the difficulty as 1-3 stars
                draw_stars_row(screen, (DISPLAY_W - 110, DISPLAY_H - 40), 3, ctx.level, 48)
            tele.frame((time.perf_counter() - now) * 1000, loop_ms, pose)
            tele.tick(screen, phase if phase != "mini" else type(mini).__name__, tracker, grabber)
            tele.draw_overlay(screen)
            pygame.display.flip()
    except Exception:                       # keep the reason in the play-test log, then stop as before
        import traceback
        tele.event("CRASH", where=phase, error=traceback.format_exc().replace("\n", " | "))
        raise
    finally:
        tele.close()
        if mini is not None:
            mini.on_exit()
        tracker.stop()
        grabber.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
