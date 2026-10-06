import sys
import cv2
import numpy as np
import pygame

from motion import MotionDetector
from kungfu import KungFuGame

CAPTURE_W = 640
CAPTURE_H = 480
DISPLAY_W = 1280
DISPLAY_H = 720
FPS       = 30


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


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(
        (DISPLAY_W, DISPLAY_H),
        pygame.HWSURFACE | pygame.DOUBLEBUF,
    )
    pygame.display.set_caption("CamToy – Kung Fu")
    clock    = pygame.time.Clock()
    font     = pygame.font.SysFont("consolas", 26, bold=True)
    font_big = pygame.font.SysFont("consolas", 54, bold=True)

    # Camera init with error screen
    try:
        cap = open_camera()
    except RuntimeError as e:
        screen.fill((18, 18, 18))
        for i, line in enumerate(str(e).split("\n")):
            surf = font.render(line, True, (255, 80, 80))
            screen.blit(surf, (48, 48 + i * 38))
        pygame.display.flip()
        while True:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.KEYDOWN):
                    pygame.quit()
                    sys.exit(1)

    detector    = MotionDetector()
    game        = KungFuGame()
    # Reusable surface – avoids allocating a new one every frame
    cam_surface = pygame.Surface((CAPTURE_W, CAPTURE_H))

    # Discard first frames while camera warms up
    for _ in range(12):
        cap.read()

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                break
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    break
                if ev.key == pygame.K_SPACE and game.state == "game_over":
                    game.reset()
        else:
            ret, frame = cap.read()
            if ret:
                mask = detector.update(frame)
                game.update(dt, mask)

                # Camera → pygame surface (reuse, no alloc)
                rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                pygame.surfarray.blit_array(cam_surface, rgb.swapaxes(0, 1))
                cam_scaled = pygame.transform.scale(cam_surface, (DISPLAY_W, DISPLAY_H))
                screen.blit(cam_scaled, (0, 0))

                game.draw(screen, font, font_big)

                fps_surf = font.render(f"{clock.get_fps():.0f}", True, (255, 255, 0))
                screen.blit(fps_surf, (10, 10))

                pygame.display.flip()
            continue
        break

    cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()
