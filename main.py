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
        self._running = True
        self._pending = None            # a new capture to switch to (handled by the reader thread)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def switch(self, cap: cv2.VideoCapture) -> None:
        """Hands over a new capture; the reader thread swaps it in between two reads."""
        self._pending = cap

    def _run(self) -> None:
        while self._running:
            if self._pending is not None:
                old, self._cap, self._pending = self._cap, self._pending, None
                old.release()
            ret, frame = self._cap.read()
            if ret:
                with self._lock:
                    self._frame = frame
                    self._seq += 1

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
    h, w = frame_rgb.shape[:2]
    s = pygame.image.frombuffer(np.ascontiguousarray(frame_rgb).tobytes(), (w, h), "RGB")
    return pygame.transform.smoothscale(s, size).convert()


def cutout_surface(frame_rgb: np.ndarray, mask: np.ndarray, size) -> pygame.Surface:
    h, w = frame_rgb.shape[:2]
    if mask.shape != (h, w):
        raise ValueError("Maske passt nicht zum Bild")
    a = (np.clip((mask - 0.35) / 0.3, 0, 1) * 255).astype(np.uint8)
    rgba = np.dstack((frame_rgb, a))
    s = pygame.image.frombuffer(np.ascontiguousarray(rgba).tobytes(), (w, h), "RGBA")
    return pygame.transform.smoothscale(s, size).convert_alpha()


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
        tracker = PoseTracker(res["grabber"], (CAPTURE_W, CAPTURE_H))
        tracker.start()
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
    from minigames.animals import AnimalGame
    from minigames.bubbles import BubbleGame
    from minigames.dressup import DressUpGame
    from minigames.kungfu_master import KungFuGame as KungFuMaster
    from minigames.pizza import PizzaGame
    from minigames.car import CarGame
    from minigames.common import draw_cursors, rainbow, text
    from minigames.pose import Pose

    grabber, tracker, ctx = res["grabber"], res["tracker"], res["ctx"]
    cam_index = res["cam_index"]
    jukebox = res["music"]

    MINIGAMES = [KungFuMaster, BubbleGame, AnimalGame, DressUpGame, PizzaGame, CarGame]
    menu = Menu(ctx, [(g.title, g.icon) for g in MINIGAMES])

    last_time = time.perf_counter()
    last_fid  = -1
    cam_surf = person_surf = cam_small = person_small = None
    mini = None

    MINI_TRACKS = ["master", "bubbles", "animals", "dressup", "pizza", "car"]
    pending, count_t, count_n = 0, 0.0, 3   # picked menu entry + its 3-2-1 countdown
    phase = "menu"               # menu -> countdown -> mini -> menu

    def goto_menu() -> None:
        nonlocal phase, mini, last_fid
        if mini is not None:
            mini.on_exit()
            mini = None
        ctx.has_mask = False
        tracker.set_segmentation(False)
        tracker.set_active(True)
        jukebox.play("menu")
        last_fid = -1
        phase = "menu"

    def begin_countdown(choice: int) -> None:
        """A game was picked with the hands: count 3-2-1, then it starts."""
        nonlocal phase, pending, count_t, count_n
        pending, count_t, count_n = choice, 0.0, 3
        ctx.play("tick")
        phase = "countdown"

    def start_mini(i: int) -> None:
        nonlocal phase, mini
        mini = MINIGAMES[i](ctx)
        tracker.set_active(True)
        jukebox.play(MINI_TRACKS[i])
        phase = "mini"

    goto_menu()

    running = True
    try:
        while running:
            clock.tick(120)   # only idles while waiting for the next camera frame
            now = time.perf_counter()

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

            # ---- menu / games: pose driven, full-frame camera picture ----
            dt = min(now - last_time, 0.1)
            last_time = now
            if tracker.error:
                screen.fill((40, 20, 30))
                text(screen, "Kamera-Fehler: " + str(tracker.error)[:70], 34,
                     (DISPLAY_W // 2, DISPLAY_H // 2))
                pygame.display.flip()
                continue

            fid, frame, lm, mask = tracker.latest()
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
                    cam_small = pygame.transform.smoothscale(cam_surf, size)
                    person_small = (pygame.transform.smoothscale(person_surf, size)
                                    if person_surf is not None else None)
            ctx.has_mask = want_mask and person_surf is not None
            if lm is not None and view:
                lm = lm.copy()
                lm[:, 0] = view[1] + lm[:, 0] * view[0]
                lm[:, 1] = view[2] + lm[:, 1] * view[0]
            pose = Pose(lm, DISPLAY_W, DISPLAY_H) if lm is not None else None

            if phase == "mini":
                mini.update(dt, pose)
                if mini.exit:
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
                veil = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
                veil.fill((20, 25, 70, 110))
                screen.blit(veil, (0, 0))
                frac = count_t - int(count_t)               # 0 -> 1 within each second
                text(screen, str(count_n), int(380 - 120 * frac),
                     (DISPLAY_W // 2, DISPLAY_H // 2 - 20), rainbow(count_n, 6, .55))
                draw_cursors(screen, pose, count_t)
            else:
                menu.draw(screen, pose)
            pygame.display.flip()
    finally:
        if mini is not None:
            mini.on_exit()
        tracker.stop()
        grabber.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
