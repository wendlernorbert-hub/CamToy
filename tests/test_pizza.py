"""Pizza game: pick a topping with a hand held on its bin, sprinkle it over the pizza, bake."""
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from minigames.common import Ctx, Sounds, Speaker  # noqa: E402
from minigames.pizza import KINDS, MAX_TOPPINGS, PizzaGame  # noqa: E402
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

    def latest(self):
        return 0, np.zeros((480, 640, 3), np.uint8), None, None


pygame.init()
screen = pygame.display.set_mode((W, H))
ctx = Ctx(W, H, Sounds(True), Speaker(), Tracker(), tempfile.mkdtemp())


def P(hand=None, other=None):
    """Standing pose with the right hand at `hand` and (optionally) the left at `other`."""
    lm = make_skeleton(PRESETS["stand"], aspect=W / H)
    for names, pos in ((("r_wr", "r_idx"), hand), (("l_wr", "l_idx"), other)):
        if pos:
            for n in names:
                lm[LM[n], 0], lm[LM[n], 1] = pos[0] / W, pos[1] / H
    return Pose(lm, W, H)


def step(g, pose, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        g.update(dt, pose)


def shot(g, name, pose=None):
    screen.fill((90, 120, 160))
    g.draw(screen, pose or P())
    pygame.image.save(screen, os.path.join(OUT, name + ".png"))


g = PizzaGame(ctx)
step(g, P(), 3.0)
check(g.state == "play", "intro leads into play")

print("pick + sprinkle")
salami = g.bins[0]
step(g, P(hand=salami.c), 0.3)
check(g.held is None, "short touch does not pick yet")
step(g, P(hand=salami.c), 0.4)
check(g.held and g.held["kind"] == "salami", "hand held 0.5 s on the bin picks the topping")
cx, cy = g.center
for i in range(60):                    # sweep the hand across the pizza
    g.update(1 / 30, P(hand=(cx - 120 + i * 4, cy - 30 + (i % 7) * 10)))
n_after = len(g.toppings)
check(n_after == 4 and g.held is None, f"one pick sprinkles 4 pieces ({n_after})")
step(g, P(hand=(cx, cy)), 1.0)
check(len(g.toppings) == n_after, "hand over the pizza without a pick adds nothing")

print("hand outside the pizza")
mush = g.bins[1]
step(g, P(hand=mush.c), 0.8)
check(g.held and g.held["kind"] == "mushroom", "second topping picked")
step(g, P(hand=(g.W * 0.25, g.H * 0.5)), 1.5)
check(len(g.toppings) == n_after and g.held, "outside the pizza nothing is dropped, topping stays in hand")

print("all kinds, then bake")
for i, b in enumerate(g.bins):
    g.held = None
    step(g, P(hand=(g.W * 0.5, g.H * 0.95)), 0.2)         # leave every bin first
    step(g, P(hand=b.c), 0.8)
    for k in range(40):
        g.update(1 / 30, P(hand=(cx - 100 + k * 5, cy + (k % 5) * 14 - 30)))
check(len({t[0] for t in g.toppings}) == len(KINDS), f"all {len(KINDS)} kinds placed ({len(g.toppings)} pieces)")
shot(g, "pizza_decorated")
step(g, P(hand=g.oven.c), 1.5)
check(g.phase == "bake", "oven button starts baking")
shot(g, "pizza_bake")
step(g, P(), 3.0)
check(g.state == "result" and g.stars >= 3, f"result with stars ({g.stars})")
step(g, P(), 1.0)
shot(g, "pizza_result")

print("limits and edge cases")
g2 = PizzaGame(ctx)
step(g2, P(), 3.0)
step(g2, P(hand=g2.oven.c), 2.0)
check(g2.phase == "decorate", "oven with an empty pizza does nothing")
for _ in range(MAX_TOPPINGS + 20):
    g2._place("olive", (g2.center[0], g2.center[1]))
check(len(g2.toppings) == MAX_TOPPINGS, f"topping count is capped at {MAX_TOPPINGS}")
g3 = PizzaGame(ctx)
step(g3, P(), 3.0)
g3._place("cheese", g3.center)
step(g3, P(), 95.0)
check(g3.state == "result", "round bakes by itself after the time limit")
g3.restart()
check(g3.state == "intro" and not g3.toppings, "restart gives a fresh pizza")

print("\n%d Fehler" % len(FAILS))
sys.exit(1 if FAILS else 0)
