"""Renders preview pictures of the menu and the games (no camera) for checking the look.

Aufruf:  python tests/preview.py [ausgabeordner] [hintergrundbild.jpg]
A real camera screenshot (e.g. from logs/*/shots) as background makes it look like in play.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np  # noqa: E402
import pygame  # noqa: E402

pygame.init()
W, H = 1280, 720
screen = pygame.display.set_mode((W, H))

from minigames.common import Ctx, Sounds, Speaker  # noqa: E402
from minigames.pose import LM, STAND, Players, Pose, make_skeleton  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "test_out"
os.makedirs(OUT, exist_ok=True)
if len(sys.argv) > 2:
    BG = pygame.transform.smoothscale(pygame.image.load(sys.argv[2]), (W, H)).convert()
else:
    BG = pygame.Surface((W, H))
    for y in range(H):
        pygame.draw.line(BG, (150 - y // 12, 160 - y // 14, 175 - y // 16), (0, y), (W, y))


class Tracker:
    def set_segmentation(self, on):
        pass


ctx = Ctx(W, H, Sounds(False), Speaker(), Tracker(), OUT)
random.seed(3)


def body(cx=0.5, s=0.8, hand=None, ground=0.97):
    lm = make_skeleton(STAND, cx=cx, s=s, aspect=W / H, ground=ground)
    if hand:
        for n in ("r_wr", "r_idx"):
            lm[LM[n], 0], lm[LM[n], 1] = hand
    return lm


def two_people(hand=None):
    """Parent with a child on the lap, like in the real play-test."""
    big = Pose(body(0.52, 1.25, ground=1.3), W, H, 0)
    small = Pose(body(0.47, 0.75, hand, ground=1.2), W, H, 1)
    return Players([big, small])


def frame(g, pose, name, dt=1 / 30, steps=1):
    for _ in range(steps):
        g.update(dt, pose)
    screen.blit(BG, (0, 0))
    g.draw_back(screen, pose)
    g.draw(screen, pose)
    pygame.image.save(screen, os.path.join(OUT, name + ".png"))


from menu import Menu  # noqa: E402
from minigames.animals import AnimalGame  # noqa: E402
from minigames.bubbles import BubbleGame  # noqa: E402
from minigames.car import CarGame  # noqa: E402
from minigames.dressup import DressUpGame  # noqa: E402
from minigames.kungfu_master import KungFuGame, Target  # noqa: E402
from minigames.pizza import PizzaGame  # noqa: E402

GAMES = [KungFuGame, BubbleGame, AnimalGame, DressUpGame, PizzaGame, CarGame]
menu = Menu(ctx, [(g.title, g.icon) for g in GAMES])
p = two_people(hand=(0.88, 0.5))
for _ in range(20):
    menu.update(1 / 30, p)
screen.blit(BG, (0, 0))
menu.draw(screen, p)
pygame.image.save(screen, os.path.join(OUT, "pv_menu.png"))

g = KungFuGame(ctx)
frame(g, two_people(), "pv_kungfu_intro", steps=20)
g.state, g.state_t = "play", 0.0
g.targets = [Target((0.13 * W, 0.30 * H), "ninja", 9), Target((0.87 * W, 0.58 * H), "ninja", 9),
             Target((0.78 * W, 0.20 * H), "boss", 9, 4)]
for tg in g.targets:
    tg.age = 1.0
g.targets[2].hp = 2
g.score, g.combo, g.last_hit, g.boss_banner = 14, 4, 0.0, 0.0
g.belt = 3
g.pows = [(0.3 * W, 0.45 * H, 0.12, 10)]
for i in range(12):                                    # let the tails settle
    g.t = 1.0 + i / 30
    g.last_hit = g.t - 0.3
    pose = two_people(hand=(0.3 + 0.02 * i, 0.45))
    g.hand_speed = {"r_wr#1": ((0.3 * W, 0.45 * H), 600.0)}
    screen.blit(BG, (0, 0))
    g.play_draw(screen, pose)
g.draw(screen, pose)
pygame.image.save(screen, os.path.join(OUT, "pv_kungfu_play.png"))
g.finish(4)
frame(g, two_people(), "pv_kungfu_result", steps=60)

for G in GAMES[1:]:
    g = G(ctx)
    frame(g, two_people(), f"pv_{G.__name__}_intro", steps=20)
    g.state, g.state_t = "play", 0.0
    g.on_play_start()
    frame(g, two_people(hand=(0.7, 0.4)), f"pv_{G.__name__}_play", steps=150)
print("ok")
