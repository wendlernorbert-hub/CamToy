import sys
import threading
import time
import cv2
import numpy as np
import pygame

import cleanup
import theme
import loading
from ink import inkify, silhouette_ink

CAPTURE_W = 640
CAPTURE_H = 480
DISPLAY_W = 1280
DISPLAY_H = 720
FPS       = 30
PLAYER_SCALE = 1.0   # Anteil des Bildschirms, den der Spieler einnimmt (unten mittig)


def open_camera(index: int = 0) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAPTURE_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_H)
    cap.set(cv2.CAP_PROP_FPS,          FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)
    if not cap.isOpened():
        raise RuntimeError(
            "Webcam konnte nicht geöffnet werden.\n"
            "Bitte prüfen:\n"
            "  Einstellungen → Datenschutz & Sicherheit\n"
            "  → Kamera → Desktop-Apps erlauben"
        )
    return cap


class FrameGrabber:
    """Reads the camera in a background thread so cap.read() blocking
    overlaps with processing/rendering instead of adding to it."""

    def __init__(self, cap: cv2.VideoCapture) -> None:
        self._cap = cap
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._seq = 0
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self._running:
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
    pygame.display.set_caption("CamToy – Kung Fu")
    clock    = pygame.time.Clock()
    font     = theme.latin(30)

    # Spieler verkleinert, unten mittig; Treffer-Maske wird identisch transformiert
    player_w, player_h = int(DISPLAY_W * PLAYER_SCALE), int(DISPLAY_H * PLAYER_SCALE)
    player_x, player_y = (DISPLAY_W - player_w) // 2, DISPLAY_H - player_h
    shrink = np.float32([[PLAYER_SCALE, 0, CAPTURE_W * (1 - PLAYER_SCALE) / 2],
                         [0, PLAYER_SCALE, CAPTURE_H * (1 - PLAYER_SCALE)]])

    # Heavy start-up work runs behind an animated loading screen
    res: dict = {}

    def load_camera() -> None:
        res["cap"] = open_camera()
        for _ in range(12):          # discard first frames while the camera warms up
            res["cap"].read()

    def load_models() -> None:
        from motion import MotionDetector
        from person import PersonSegmenter     # pulls in mediapipe (slow import)
        res["detector"]  = MotionDetector()
        res["segmenter"] = PersonSegmenter()

    def load_scene() -> None:
        from background import build_background
        res["background"] = build_background()

    def load_game() -> None:
        from kungfu import KungFuGame
        from position import PositionGuide
        res["game"]  = KungFuGame()
        res["guide"] = PositionGuide((player_w, player_h))

    err = loading.run(screen, [
        ("Kamera wird geöffnet …",   3, load_camera),
        ("Erkennung wird geladen …", 4, load_models),
        ("Tusche wird gerieben …",   3, load_scene),
        ("Dojo wird vorbereitet …",  1, load_game),
    ])
    if err is not None:
        if not isinstance(err, RuntimeError):
            raise err
        screen.fill(theme.PAPER)
        for i, line in enumerate(str(err).split("\n")):
            surf = font.render(line, True, theme.VERMILION if i == 0 else theme.INK)
            screen.blit(surf, (48, 48 + i * 42))
        pygame.display.flip()
        while True:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.KEYDOWN):
                    pygame.quit()
                    sys.exit(1)

    cap, detector, segmenter = res["cap"], res["detector"], res["segmenter"]
    background, game, guide  = res["background"], res["game"], res["guide"]
    # Reusable surfaces – avoid allocating new ones every frame
    cam_surface = pygame.Surface((CAPTURE_W, CAPTURE_H), pygame.SRCALPHA)
    cam_scaled  = pygame.Surface((player_w, player_h), pygame.SRCALPHA)

    grabber   = FrameGrabber(cap)
    last_seq  = 0
    last_time = time.perf_counter()

    game.reset()
    phase     = "position"   # position (T-pose + countdown) -> play

    try:
        while True:
            clock.tick(120)   # only idles while waiting for the next camera frame

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    break
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        break
                    if ev.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                    if ev.key == pygame.K_SPACE and game.state == "game_over":
                        game.reset()
                        guide.reset()
                        phase = "position"
            else:
                seq, frame = grabber.latest()
                if frame is not None and seq != last_seq:
                    last_seq = seq
                    now = time.perf_counter()
                    dt = min(now - last_time, 0.05)
                    last_time = now

                    motion = detector.update(frame)
                    person, hit_zone = segmenter.refine(cv2.flip(segmenter.update(frame), 1))

                    # Nur bewegte Körperteile (inkl. Hände knapp außerhalb der Maske) zählen
                    if phase == "position":
                        if guide.update(dt, person):
                            phase = "play"
                    else:
                        hit = cv2.bitwise_and(motion, hit_zone)
                        game.update(dt, cv2.warpAffine(hit, shrink, (CAPTURE_W, CAPTURE_H),
                                                       flags=cv2.INTER_NEAREST))

                    # Tusche-Look; Person mit Pinsel-Kontur per Alpha-Maske über den Hintergrund legen
                    painting = inkify(cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB))
                    alpha = silhouette_ink(painting, person)
                    pygame.surfarray.blit_array(cam_surface, painting.swapaxes(0, 1))
                    pygame.surfarray.pixels_alpha(cam_surface)[:] = alpha.T
                    pygame.transform.smoothscale(cam_surface, (player_w, player_h), cam_scaled)
                    screen.blit(background, (0, 0))
                    screen.blit(cam_scaled, (player_x, player_y))

                    if phase == "position":
                        guide.draw(screen, (player_x, player_y))
                    else:
                        game.draw(screen)

                    fps_surf = font.render(f"{clock.get_fps():.0f}", True, theme.INK_SOFT)
                    screen.blit(fps_surf, (30, 26))

                    pygame.display.flip()
                continue
            break
    finally:
        grabber.stop()
        segmenter.close()
        cap.release()
        pygame.quit()


if __name__ == "__main__":
    main()
