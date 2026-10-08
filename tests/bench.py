"""Frame-time benchmark without camera: simulated body, the real drawing code at 1280x720.

Aufruf:  python tests/bench.py
Prints the average/worst milliseconds per frame for the camera conversion, the menu and every game.
"""
import math
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from main import DISPLAY_H as H, DISPLAY_W as W, cutout_surface, to_surface  # noqa: E402
from minigames.common import Ctx, Sounds, Speaker  # noqa: E402
from minigames.pose import LM, STAND, Pose, make_skeleton  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((W, H))


class MockTracker:
    def set_segmentation(self, on):
        pass

    def set_active(self, on):
        pass


ctx = Ctx(W, H, Sounds(True), Speaker(), MockTracker(), tempfile.mkdtemp())
rng = np.random.default_rng(1)
frame = rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)
mask = np.zeros((480, 640), np.float32)
mask[80:480, 200:440] = 1.0


def pose_at(t):
    """Standing body whose hands sweep around, so the games get hits and particles."""
    lm = make_skeleton(STAND, aspect=W / H)
    for i, s in enumerate("lr"):
        x = 0.5 + (0.38 if s == "r" else -0.38) * math.cos(t * 2.1 + i)
        y = 0.45 + 0.3 * math.sin(t * 2.7 + i)
        for p in ("wr", "idx"):
            lm[LM[f"{s}_{p}"], 0], lm[LM[f"{s}_{p}"], 1] = x, y
    return Pose(lm, W, H)


def bench(name, step, frames=240):
    times = []
    for i in range(frames):
        t0 = time.perf_counter()
        step(i / 60)
        times.append((time.perf_counter() - t0) * 1000)
    times = times[20:]
    print(f"{name:22s} avg {np.mean(times):6.2f} ms   p95 {np.percentile(times, 95):6.2f}   max {max(times):6.2f}")


bench("to_surface", lambda t: to_surface(frame, (W, H)))
bench("cutout_surface", lambda t: cutout_surface(frame, mask, (W, H)))
cam = to_surface(frame, (W, H))

from menu import Menu  # noqa: E402

menu = Menu(ctx, [("x", lambda s, c, r: None)] * 6)


def menu_step(t):
    p = pose_at(t)
    menu.update(1 / 60, p)
    screen.blit(cam, (0, 0))
    menu.draw(screen, p)


bench("menu", menu_step)

from minigames.animals import AnimalGame  # noqa: E402
from minigames.bubbles import BubbleGame  # noqa: E402
from minigames.car import CarGame  # noqa: E402
from minigames.dressup import DressUpGame  # noqa: E402
from minigames.kungfu_master import KungFuGame  # noqa: E402
from minigames.pizza import PizzaGame  # noqa: E402

for G in (KungFuGame, BubbleGame, AnimalGame, DressUpGame, PizzaGame, CarGame):
    for level in (1, 3):
        ctx.level = level
        g = G(ctx)
        g.state, g.state_t = "play", 0.0
        g.on_play_start()

        def step(t, g=g):
            p = pose_at(t)
            g.update(1 / 60, p)
            screen.blit(cam, (0, 0))
            g.draw_back(screen, p)
            g.draw(screen, p)

        bench(f"{G.__name__} L{level}", step, 300)
        g.on_exit()
