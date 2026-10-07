"""CamToy - Bewegungsspiele für Kinder mit der Webcam (EyeToy-Idee, 2026er Technik).

Start:  python main.py            (Webcam)
        python main.py --maus     (ohne Kamera, Maus statt Hand - zum Testen)
Tasten: ESC zurück/Ende | 1 2 3 Schwierigkeit | F11 Vollbild | D Skelett-Anzeige
"""
import argparse
import os
import sys

import numpy as np
import pygame

from animals import AnimalGame
from bubbles import BubbleGame
from common import Ctx, DwellButton, Sounds, Speaker, circle_alpha, draw_cursors, rainbow, text
from dressup import DressUpGame
from kungfu import KungFuGame
from pose import BONES, Pose
from tracker import MockTracker, Tracker

GAMES = [BubbleGame, DressUpGame, AnimalGame, KungFuGame]
TILE_COLORS = [(90, 190, 255), (255, 140, 205), (110, 215, 120), (255, 170, 70)]


def to_surface(frame, size):
    h, w = frame.shape[:2]
    s = pygame.image.frombuffer(np.ascontiguousarray(frame).tobytes(), (w, h), "RGB")
    return pygame.transform.smoothscale(s, size).convert()


def cutout_surface(frame, mask, size):
    h, w = frame.shape[:2]
    if mask.shape != (h, w):
        raise ValueError("Maske passt nicht zum Bild")
    a = (np.clip((mask - 0.35) / 0.3, 0, 1) * 255).astype(np.uint8)
    rgba = np.dstack((frame, a))
    s = pygame.image.frombuffer(np.ascontiguousarray(rgba).tobytes(), (w, h), "RGBA")
    return pygame.transform.smoothscale(s, size).convert_alpha()


class Menu:
    def __init__(self, ctx):
        self.ctx, self.W, self.H = ctx, ctx.W, ctx.H
        self.t = 0.0
        xs, ys = (self.W * 0.28, self.W * 0.72), (self.H * 0.34, self.H * 0.72)
        self.tiles = []
        for i, g in enumerate(GAMES):
            self.tiles.append(DwellButton((xs[i % 2], ys[i // 2]), 105, 1.1))

    def update(self, dt, pose):
        self.t += dt
        hands = pose.hand_points() if pose else []
        for i, tile in enumerate(self.tiles):
            if tile.update(dt, hands):
                self.ctx.play("click")
                return i
        return None

    def draw(self, surf, pose):
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((30, 40, 100, 90))
        surf.blit(veil, (0, 0))
        title = "CamToy"
        f_w = 62
        x = self.W / 2 - len(title) * f_w / 2 + f_w / 2
        for i, ch in enumerate(title):
            text(surf, ch, 92, (x + i * f_w, 62 + 6 * np.sin(self.t * 3 + i)), rainbow(i, 6, .6))
        for i, (g, tile) in enumerate(zip(GAMES, self.tiles)):
            r = int(tile.r * (1.06 if tile.hover else 1.0) * (1 + 0.015 * np.sin(self.t * 2.5 + i)))
            circle_alpha(surf, TILE_COLORS[i] + (210,), tile.c, r)
            pygame.draw.circle(surf, (255, 255, 255), tile.c, r, 6)
            g.icon(surf, tile.c, int(r * 0.72))
            from common import draw_ring
            draw_ring(surf, tile.c, r + 16, r + 6, tile.progress, (255, 225, 60))
            text(surf, g.title, 40, (tile.c[0], tile.c[1] + r + 34))
        lv = self.ctx.level
        from common import draw_stars_row
        draw_stars_row(surf, (90, self.H - 36), 3, lv, 26)
        if not (pose and pose.ok):
            text(surf, "Stell dich vor die Kamera und winke!", 40, (self.W / 2, self.H - 36), (255, 240, 140))
        draw_cursors(surf, pose, self.t)


def run():
    ap = argparse.ArgumentParser(description="CamToy - Webcam-Bewegungsspiele für Kinder")
    ap.add_argument("--kamera", type=int, default=0, help="Kamera-Nummer (Standard 0)")
    ap.add_argument("--maus", action="store_true", help="ohne Kamera, Maus als Hand")
    ap.add_argument("--leise", action="store_true", help="ohne Ton")
    ap.add_argument("--keine-sprache", action="store_true", help="ohne Sprachausgabe")
    ap.add_argument("--vollbild", action="store_true")
    ap.add_argument("--hoehe", type=int, default=720, help="Fensterhöhe in Pixeln")
    args = ap.parse_args()

    tracker = MockTracker() if args.maus else Tracker(args.kamera)
    try:
        tracker.start()
    except Exception as e:  # noqa: BLE001
        print("\nFehler:", e)
        sys.exit(1)
    aspect = tracker.size[0] / tracker.size[1]
    H = args.hoehe
    W = int(round(H * aspect / 2) * 2)

    pygame.init()
    pygame.display.set_caption("CamToy")
    flags = pygame.SCALED | (pygame.FULLSCREEN if args.vollbild else 0)
    screen = pygame.display.set_mode((W, H), flags)
    here = os.path.dirname(os.path.abspath(__file__))
    ctx = Ctx(W, H, Sounds(not args.leise), Speaker(not args.keine_sprache), tracker, here)
    ctx.has_mask = False
    menu, game = Menu(ctx), None
    clock = pygame.time.Clock()
    cam_surf = person_surf = None
    last_fid = -1
    running = True

    def leave():
        nonlocal game
        if game:
            game.on_exit()
        game = None

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.1)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if game:
                        leave()
                    else:
                        running = False
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    ctx.level = e.key - pygame.K_0
                elif e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif e.key == pygame.K_d:
                    ctx.debug = not ctx.debug
        if args.maus:
            mx, my = pygame.mouse.get_pos()
            tracker.mouse = (mx / W, my / H, pygame.mouse.get_pressed()[0])
        if tracker.error:
            screen.fill((40, 20, 30))
            text(screen, "Kamera-Fehler:", 50, (W // 2, H // 2 - 40))
            text(screen, str(tracker.error)[:70], 30, (W // 2, H // 2 + 20))
            pygame.display.flip()
            continue

        fid, frame, lm, mask = tracker.latest()
        want_mask = bool(game and game.needs_mask)
        if frame is not None and fid != last_fid:
            last_fid = fid
            cam_surf = to_surface(frame, (W, H))
            person_surf = None
            if want_mask and mask is not None:
                try:
                    person_surf = cutout_surface(frame, mask, (W, H))
                except Exception:  # noqa: BLE001
                    person_surf = None
        ctx.has_mask = want_mask and person_surf is not None
        pose = Pose(lm, W, H) if lm is not None else None

        if game:
            game.update(dt, pose)
            if game.exit:
                leave()
        else:
            sel = menu.update(dt, pose)
            if sel is not None:
                game = GAMES[sel](ctx)

        if cam_surf:
            screen.blit(cam_surf, (0, 0))
        else:
            screen.fill((60, 80, 120))
        if game:
            game.draw_back(screen, pose)
            if ctx.has_mask:
                screen.blit(person_surf, (0, 0))
            game.draw(screen, pose)
        else:
            menu.draw(screen, pose)
        if ctx.debug:
            if pose:
                for a, b in BONES:
                    if pose.has(a, b, thr=0.3):
                        pygame.draw.line(screen, (255, 255, 0), pose.P(a), pose.P(b), 3)
            text(screen, "Kamera %.0f fps | %.0f fps" % (tracker.fps, clock.get_fps()), 26, (W - 170, H - 20))
        pygame.display.flip()

    leave()
    tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    run()
