"""Car game: both hands turn the wheel (angle of the line left hand -> right hand)."""
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from minigames.car import CarGame, DURATION, LEVELS, Obj  # noqa: E402
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
    seg = None

    def set_segmentation(self, on):
        self.seg = on


pygame.init()
screen = pygame.display.set_mode((W, H))
tracker = Tracker()
ctx = Ctx(W, H, Sounds(True), Speaker(), tracker, ".")


def hands_pose(angle_deg=0.0, mid=(640, 520), dist=300, left_only=False):
    """Both hands on a wheel turned by angle_deg (clockwise > 0)."""
    a = math.radians(angle_deg)
    dx, dy = math.cos(a) * dist / 2, math.sin(a) * dist / 2
    lm = make_skeleton(PRESETS["stand"], aspect=W / H)
    pts = {"l": (mid[0] - dx, mid[1] - dy), "r": (mid[0] + dx, mid[1] + dy)}
    for side in "lr":
        if left_only and side == "r":
            lm[LM["r_wr"], 2] = lm[LM["r_idx"], 2] = 0.0
            continue
        for n in (f"{side}_wr", f"{side}_idx"):
            lm[LM[n], 0], lm[LM[n], 1] = pts[side][0] / W, pts[side][1] / H
    return Pose(lm, W, H)


def step(g, pose, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        g.update(dt, pose)


def start():
    ctx.level = 1
    g = CarGame(ctx)
    step(g, hands_pose(), 3.0)             # intro
    return g


print("Setup")
g = start()
check(g.state == "play", "intro leads into play")
check(tracker.seg is True, "asks the tracker for the person mask")
check(CarGame.needs_mask and CarGame.view[0] < 1, "player is shown scaled into the car")

print("Wheel reading")
g = start()
step(g, hands_pose(0), 0.6)
check(abs(g.ang) < 3, f"level hands -> wheel straight ({g.ang:.1f} deg)")
step(g, hands_pose(30), 0.8)
check(25 < g.ang < 33, f"right hand lower -> wheel turns clockwise ({g.ang:.1f} deg)")
step(g, hands_pose(-30), 0.8)
check(-33 < g.ang < -25, f"left hand lower -> wheel turns counter-clockwise ({g.ang:.1f} deg)")
step(g, hands_pose(30, mid=(400, 480), dist=420), 0.6)
check(abs(g.hand_mid[0] - 400) < 25 and g.wheel_r > 150, "wheel follows the hands (centre and size)")
step(g, hands_pose(10, dist=40), 0.5)
check(g.wheel_r > 100, "hands almost touching are ignored (wheel size unchanged)")

print("Steering")
g = start()
x0 = g.x
step(g, hands_pose(35), 1.5)
check(g.x > x0 + 0.5, f"steering right moves the car right ({x0:.2f} -> {g.x:.2f})")
g = start()
step(g, hands_pose(-35), 1.5)
check(g.x < -0.5, f"steering left moves the car left ({g.x:.2f})")
g = start()
step(g, hands_pose(0), 2.0)
check(abs(g.x) < 0.2, f"straight on the straight stretch stays centred ({g.x:.2f})")
g = start()
step(g, hands_pose(2), 2.0)
check(abs(g.x) < 0.2, "tiny wheel angle is inside the dead zone")

print("No hands")
g = start()
step(g, hands_pose(30), 0.8)
step(g, None, 2.0)
check(not g.have_hands and abs(g.ang) < 6, f"hands gone -> wheel eases back ({g.ang:.1f} deg)")
check(g.state == "play" and g.pos > 0, "the car keeps driving")
g = start()
step(g, hands_pose(20, left_only=True), 1.0)
check(not g.have_hands or True, "one hand only does not crash")

print("Objects")
g = start()
g.objs = [Obj("coin", g.pos + 8.0, g.x)]
step(g, hands_pose(0), 1.0)
check(g.coins == 1, f"coin straight ahead is collected ({g.coins})")
g = start()
g.objs = [Obj("coin", g.pos + 8.0, g.x + 0.8)]
step(g, hands_pose(0), 1.0)
check(g.coins == 0, "coin in the other lane is missed")
g = start()
v0 = g.speed
g.objs = [Obj("cone", g.pos + 8.0, g.x)]
step(g, hands_pose(0), 0.5)
check(g.bump_t > 0 and g.speed < v0 * 0.8, f"cone hit slows the car ({v0:.0f} -> {g.speed:.0f})")
step(g, hands_pose(0), 3.5)
check(g.speed > v0 * 0.9 and g.state == "play", "speed recovers, no game over")
g = start()
g.x = 1.25
step(g, hands_pose(0), 1.5)
check(g.speed < LEVELS[1]["speed"] * 0.7, f"driving off the road is slow ({g.speed:.0f})")

print("Regression: coin sparkle ring must never get a negative alpha (crashed on real frame times)")
for dt in (1 / 60, 1 / 30, 0.05, 0.1, 0.037):
    g = start()
    for k in range(40):
        g.objs.append(Obj("coin", g.pos + 3.0 + k * 4.0, g.x))        # a stream of coins right ahead
    ok = True
    try:
        for _ in range(int(6 / dt)):
            g.update(dt, hands_pose(0))
            screen.fill((0, 0, 0))
            g.draw_back(screen, hands_pose(0))
            g.draw(screen, hands_pose(0))
    except Exception as e:  # noqa: BLE001
        ok = False
        print("   ", type(e).__name__, e)
    check(ok and g.coins > 5, f"collecting coins and drawing at dt={dt:.3f} works ({g.coins} coins)")

print("A full round (simple autopilot steers toward the next coin)")
for lv in (1, 2, 3):
    ctx.level = lv
    g = CarGame(ctx)
    step(g, hands_pose(0), 3.0)
    t = 0.0
    while g.state == "play" and t < DURATION + 5:
        ahead = [o for o in g.objs if o.kind == "coin" and 2 < o.z - g.pos < 40]
        ahead.sort(key=lambda o: o.z)
        want = ahead[0].x if ahead else 0.0
        # keep away from cones directly ahead
        for o in g.objs:
            if o.kind == "cone" and 2 < o.z - g.pos < 25 and abs(o.x - g.x) < 0.45:
                want = g.x + (0.7 if o.x < g.x else -0.7)
        ang = max(-40, min(40, (want - g.x) * 55))
        g.update(1 / 30, hands_pose(ang))
        t += 1 / 30
    check(g.state == "result", f"level {lv}: round ends by itself ({g.stars} stars, {g.coins} coins)")
    check(g.coins >= 10, f"level {lv}: steering collects coins ({g.coins})")

print("Render")
ctx.level = 1
g = CarGame(ctx)
step(g, hands_pose(0), 3.0)
for _ in range(120):
    g.update(1 / 30, hands_pose(14))
screen.fill((0, 0, 0))
g.draw_back(screen, hands_pose(14))
g.draw(screen, hands_pose(14))
pygame.image.save(screen, os.path.join(OUT, "car_play.png"))
g2 = CarGame(ctx)
screen.fill((0, 0, 0))
g2.draw_back(screen, None)
g2.draw(screen, None)
pygame.image.save(screen, os.path.join(OUT, "car_noHands.png"))
g.finish(4)
step(g, hands_pose(0), 1.5)
screen.fill((30, 40, 80))
g.draw(screen, hands_pose(0))
pygame.image.save(screen, os.path.join(OUT, "car_result.png"))
check(True, "screenshots written")

print("\n%d Fehler" % len(FAILS))
sys.exit(1 if FAILS else 0)
