"""Result screen: no buttons in the bottom middle; home is top left, replay top right."""
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from minigames.animals import AnimalGame  # noqa: E402
from minigames.bubbles import BubbleGame  # noqa: E402
from minigames.car import CarGame  # noqa: E402
from minigames.common import Ctx, Sounds, Speaker  # noqa: E402
from minigames.kungfu_master import KungFuGame  # noqa: E402
from minigames.pizza import PizzaGame  # noqa: E402
from minigames.pose import LM, PRESETS, Pose, make_skeleton  # noqa: E402

W, H = 1280, 720
OUT = sys.argv[1] if len(sys.argv) > 1 else "test_out"
os.makedirs(OUT, exist_ok=True)
FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


class Tracker:
    size = (640, 480)
    error = None

    def set_segmentation(self, on):
        pass


pygame.init()
screen = pygame.display.set_mode((W, H))
ctx = Ctx(W, H, Sounds(True), Speaker(), Tracker(), ".")


def P(hand=None):
    lm = make_skeleton(PRESETS["stand"], aspect=W / H)
    if hand:
        for n in ("r_wr", "r_idx"):
            lm[LM[n], 0], lm[LM[n], 1] = hand[0] / W, hand[1] / H
    return Pose(lm, W, H)


def step(g, pose, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        g.update(dt, pose)


for cls in (KungFuGame, BubbleGame, AnimalGame, PizzaGame, CarGame):
    print(cls.__name__)
    g = cls(ctx)
    check(not hasattr(g, "btn_home"), "no bottom home button any more")
    step(g, P(), 3.0)
    g.finish(3)
    step(g, P(), 1.5)
    check(g.state == "result", "result screen reached")
    bx, by = g.btn_again.c
    check(bx > W * 0.8 and by < H * 0.2, f"replay button is top right ({bx:.0f}, {by:.0f})")
    check(bx < W - 2 * g.btn_again.r and by > g.btn_again.r + 8, "...and not squeezed into the very corner")
    hx, hy = g.home.c
    check(hx < W * 0.1 and hy < H * 0.15, "home button is top left")
    # a hand held on the old bottom-centre spots does nothing
    for x in (W / 2 - 120, W / 2 + 120):
        step(g, P(hand=(x, H * 0.83)), 1.5)
    check(g.state == "result" and not g.exit, "hand on the old bottom buttons does nothing")
    screen.fill((90, 120, 160))
    g.draw_back(screen, P())
    g.draw(screen, P())
    pygame.image.save(screen, os.path.join(OUT, f"result_{cls.__name__}.png"))
    # home still works on the result screen
    g.exit = False
    step(g, P(hand=g.home.c), 2.0)
    check(g.exit, "hand on the top-left home button leaves the game")
    # replay works
    g2 = cls(ctx)
    step(g2, P(), 3.0)
    g2.finish(2)
    step(g2, P(), 1.0)
    step(g2, P(hand=g2.btn_again.c), 1.5)
    check(g2.state in ("intro", "play"), "hand on the top-right replay button starts a new round")

print("%d Fehler" % len(FAILS))
sys.exit(1 if FAILS else 0)
