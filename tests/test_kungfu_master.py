"""Kung-Fu-Meister: blue player ninja, red ninjas, boss that needs several hits."""
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from minigames import kungfu_master as km  # noqa: E402
from minigames.common import Ctx, Sounds, Speaker  # noqa: E402
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


def P(hand=None, hide_head=False):
    lm = make_skeleton(PRESETS["stand"], aspect=W / H)
    if hand:
        for n in ("r_wr", "r_idx"):
            lm[LM[n], 0], lm[LM[n], 1] = hand[0] / W, hand[1] / H
    if hide_head:
        for n in ("nose", "l_eye", "r_eye", "l_ear", "r_ear"):
            lm[LM[n], 2] = 0.0
    return Pose(lm, W, H)


def step(g, pose, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        g.update(dt, pose)


def swing(g, x, y, frames=6, speed_px=60):
    """A fast sweep of the right hand through (x, y)."""
    for k in range(frames):
        g.update(1 / 30, P(hand=(x + (k - frames // 2) * speed_px, y)))


def fresh(level=1):
    ctx.level = level
    g = km.KungFuGame(ctx)
    step(g, P(), 3.0)
    g.targets = []
    return g


def boss_of(g):
    return next((t for t in g.targets if t.kind == "boss"), None)


print("Look")
check(km.draw_ninja.__defaults__[0] == "red", "enemies are red ninjas by default")
g = fresh()
for pose in (P(), P(hide_head=True), None):
    screen.fill((90, 120, 160))
    g.draw(screen, pose)
check(True, "player costume draws with head, without head and without any pose")

print("Normal ninjas")
g = fresh()
g.targets = [km.Target((300, 300), "ninja", 5.0)]
step(g, P(), 0.5)
swing(g, 300, 300)
check(g.score == 1 and g.kills_since_boss == 1, "one hit defeats a red ninja and counts towards the boss")

print("Boss appears after enough kills")
for lv in (1, 2, 3):
    g = fresh(lv)
    need = km.BOSS[lv]["every"]
    g.kills_since_boss = need - 1
    step(g, P(), 3.0)
    check(boss_of(g) is None, f"level {lv}: no boss before {need} kills")
    g.kills_since_boss = need
    step(g, P(), 1.5)
    b = boss_of(g)
    check(b is not None and b.hp == km.BOSS[lv]["hp"] and g.boss_banner > 0,
          f"level {lv}: boss with {km.BOSS[lv]['hp']} hit points and a BOSS! banner")
    check(g.kills_since_boss == 0, f"level {lv}: kill counter resets")
    step(g, P(), 0.5)
    check(len([t for t in g.targets if t.kind == "boss"]) == 1, f"level {lv}: only one boss at a time")

print("Boss fight")
g = fresh(1)
g.kills_since_boss = km.BOSS[1]["every"]
step(g, P(), 1.5)
b = boss_of(g)
hp0 = b.hp
score0 = g.score
rest = (b.x, b.y)
step(g, P(hand=rest), 0.6)                    # the hand arrives (its jump may count once) ...
b.hp, b.last_hit = hp0, -9.0                  # ... then forget that and let it rest
step(g, P(hand=rest), 2.0)
check(b.hp == hp0 and not b.hit, "a hand resting on the boss does nothing")
swing(g, b.x, b.y)
check(b.hp == hp0 - 1 and not b.hit, f"one swing = one hit ({b.hp}/{hp0} left, boss still there)")
check(b.flash > 0 and b.shake > 0, "boss flashes and shakes when hit")
hp1 = b.hp
swing(g, b.x, b.y, frames=4)                  # more frames right away: inside the cooldown
check(b.hp == hp1, "frames inside the cooldown do not count again")
for _ in range(hp1):
    step(g, P(), km.BOSS_COOLDOWN + 0.1)
    swing(g, b.x, b.y)
check(b.hit and b.hp == 0, "after all hits the boss is knocked out")
check(g.score >= score0 + hp0 + km.BOSS_KILL_POINTS, f"hits and a kill bonus count for the belt (score {g.score})")
check(g.state == "play", "game continues after the boss")

print("Boss escapes")
g = fresh(2)
g.kills_since_boss = km.BOSS[2]["every"]
step(g, P(), 1.5)
b = boss_of(g)
score0, state0 = g.score, g.state
step(g, P(), km.BOSS[2]["life"] + 1.0)
check(boss_of(g) is None and g.score == score0 and g.state == state0, "unbeaten boss leaves without penalty")

print("Full rounds do not crash (random swings, all levels)")
import random  # noqa: E402
random.seed(5)
for lv in (1, 2, 3):
    g = fresh(lv)
    ok = True
    try:
        for i in range(int(km.KungFuGame.DURATION * 30) + 60):
            tg = [t for t in g.targets if not t.hit and t.age > 0.35]
            if tg and random.random() < 0.5:
                t0 = random.choice(tg)
                g.update(1 / 30, P(hand=(t0.x + random.uniform(-80, 80), t0.y + random.uniform(-60, 60))))
            else:
                g.update(1 / 30, P(hand=(random.uniform(0, W), random.uniform(0, H))))
            if i % 4 == 0:
                screen.fill((90, 120, 160))
                g.draw(screen, P())
    except Exception as e:  # noqa: BLE001
        ok = False
        import traceback
        traceback.print_exc()
    check(ok and g.state == "result", f"level {lv}: round ran to the end (score {g.score})")

print("Screenshots")
g = fresh(2)
g.kills_since_boss = km.BOSS[2]["every"]
step(g, P(), 1.0)
b = boss_of(g)
swing(g, b.x, b.y)
screen.fill((90, 120, 160))
g.draw(screen, P())
pygame.image.save(screen, os.path.join(OUT, "kf_boss.png"))
check(True, "written")

print("\n%d Fehler" % len(FAILS))
sys.exit(1 if FAILS else 0)
