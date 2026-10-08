"""Pizza game: whole ingredients are made ready (knife / blender -> sauce / grater -> cheese),
put on the plain dough (pieces, smeared sauce, sprinkled cheese), baked in the stone oven,
sliced and eaten by a boy."""
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from minigames.common import Ctx, Sounds, Speaker  # noqa: E402
from minigames.pizza import BAKE_TIME, HOVER_CUT, KINDS, MAX_TOPPINGS, PIECES, TOOL, WORK, PizzaGame  # noqa: E402
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
ctx = Ctx(W, H, Sounds(True), Speaker(), Tracker(), tempfile.mkdtemp())


def P(hand=None):
    """Standing pose with the right hand at `hand` (the left hand hangs down, out of the way)."""
    lm = make_skeleton(PRESETS["stand"], aspect=W / H)
    for n in ("l_wr", "l_idx"):
        lm[LM[n], 2] = 0.0
    for n in ("r_wr", "r_idx"):
        if hand:
            lm[LM[n], 0], lm[LM[n], 1] = hand[0] / W, hand[1] / H
        else:
            lm[LM[n], 2] = 0.0
    return Pose(lm, W, H)


def step(g, pose, seconds, dt=1 / 30):
    for _ in range(int(round(seconds / dt))):
        g.update(dt, pose)


def shot(g, name, pose=None):
    screen.fill((90, 120, 160))
    g.draw(screen, pose or P())
    pygame.image.save(screen, os.path.join(OUT, name + ".png"))


def bin_of(g, kind):
    return next(b for b in g.bins if b.kind == kind)


def stroke(g, down=True):
    """One fast stroke through the station (down: knife; down or up: grater)."""
    sx, sy = g.station
    for i in range(6):
        g.update(1 / 30, P((sx, sy - 130 + i * 40) if down else (sx, sy + 70 - i * 40)))
    for i in range(10):                     # move away slowly
        g.update(1 / 30, P((sx + 260, sy + 40 - i * 4)))


def take(g):
    """Take the knife (or the piece of cheese) that lies at the station."""
    tool = TOOL.get(g.item["kind"], "knife")
    step(g, P(g._tool_rest(tool)), 0.1)


def pick(g, kind):
    step(g, P((W / 2, H * 0.95)), 0.3)
    g.carry.clear()
    step(g, P(bin_of(g, kind).c), 0.8)


def put_piece(g, at):
    sx, sy = g.station
    step(g, P((sx, sy)), 0.1)                        # touch the bowl: a piece sticks to the hand
    for i in range(12):                               # carry it over to the pizza
        g.update(1 / 30, P((sx + (at[0] - sx) * i / 11, sy + (at[1] - sy) * i / 11)))
    step(g, P(at), 0.6)                               # hold still: it is put down


def sweep(g, rounds=2):
    """Take from the bowl, then move the hand around over the pizza."""
    sx, sy = g.station
    step(g, P((sx, sy)), 0.1)
    cx, cy = g.center
    for i in range(int(rounds * 60)):
        a = i / 60 * 6.28
        g.update(1 / 30, P((cx + np.cos(a * 1.3) * 110, cy + np.sin(a) * 110)))


g = PizzaGame(ctx)
step(g, P(), 3.0)
check(g.state == "play", "intro leads into play")
check(g.sauce_dabs == 0 and not g.toppings, "the pizza starts as plain dough (no sauce)")

print("salami: knife")
sal = bin_of(g, "salami")
step(g, P(sal.c), 0.3)
check(g.item is None, "short touch does not pick yet")
step(g, P(sal.c), 0.5)
check(g.item and g.item["kind"] == "salami" and g.item["work"] == 0, "hand held on the bin puts the whole salami on the board")
shot(g, "pizza_whole", P(sal.c))
kx, ky = g._tool_rest("knife")
cut_x, cut_y = g._cut_point()
check(ky < cut_y and abs(kx - cut_x) < 30, "the knife waits right over the ingredient")
sx0, sy0 = g.station
step(g, P((sx0 + 260, sy0 + 40)), 1.0)
check(g.item["work"] == 0 and g.tool_hand is None, "a hand away from the board neither takes the knife nor cuts")
step(g, P((kx, ky)), 0.1)
check(g.tool_hand is not None, "touching the waiting knife takes it")
step(g, P((cut_x, cut_y - 30)), HOVER_CUT[1] + 0.05)
check(g.item["work"] == 1, f"just holding the knife over the ingredient cuts (no chop needed) ({g.item['work']})")
shot(g, "pizza_knife_hover", P((cut_x, cut_y - 30)))
for _ in range(WORK["knife"] - 2):
    stroke(g)
check(g.item and g.item["work"] == WORK["knife"] - 1, f"a fast downward stroke is a cut too ({g.item and g.item['work']})")
shot(g, "pizza_cutting")
stroke(g)
check(g.item is None and g.bowl and g.bowl["mode"] == "piece" and g.bowl["left"] == PIECES and not g.carry,
      "after the last cut the slices are in the bowl (and the cutting hand did not grab one)")
step(g, P(), 0.8)
cx, cy = g.center
step(g, P((cx - 60, cy)), 0.6)
check(not g.toppings, "a hand over the pizza without a piece puts nothing down")
put_piece(g, (cx - 60, cy - 20))
check(len(g.toppings) == 1 and not g.carry, f"piece carried over and put down by holding still ({len(g.toppings)})")
put_piece(g, (cx + 50, cy + 30))
check(len(g.toppings) == 2 and g.bowl["left"] == PIECES - 2, "one piece per trip")

print("a hand that still holds something can pick a new ingredient (play-test bug)")
sx, sy = g.station
step(g, P((sx, sy)), 0.1)                            # take a salami slice ...
check(bool(g.carry), "the hand holds a slice")
step(g, P(bin_of(g, "tomato").c), 0.8)                # ... and go straight to the tomatoes
check(g.item and g.item["kind"] == "tomato" and not g.carry, "the full hand picked the tomatoes")

print("tomato: the blender makes sauce by itself")
pick(g, "tomato")
check(g.item and g.item["kind"] == "tomato", "tomatoes picked")
step(g, P(), 0.8)
check(g.item is not None, "the blender is still running")
step(g, P(), 1.0)
check(g.bowl and g.bowl["mode"] == "sauce", "without any hand motion the tomatoes become a pot of sauce")
shot(g, "pizza_sauce_pot")
step(g, P(), 0.8)
sweep(g)
check(g.sauce_dabs > 20 and g.sauce_coverage() > 0.15,
      f"moving the hand over the pizza smears sauce ({g.sauce_dabs} dabs, {g.sauce_coverage():.0%} covered)")
for i in range(400):                                   # keep going, in a spiral: one pot covers it all
    a, rad = i * 0.25, 10 + 140 * (i % 200) / 200
    g.update(1 / 30, P((cx + np.cos(a) * rad, cy + np.sin(a) * rad)))
check(g.sauce_coverage() > 0.85, f"one pot of sauce is enough for the whole pizza ({g.sauce_coverage():.0%})")
shot(g, "pizza_sauced")

print("cheese: grater")
pick(g, "cheese")
take(g)
check(g.tool_hand is not None, "the hand took the piece of cheese")
for i in range(WORK["grater"]):
    stroke(g, down=i % 2 == 0)
check(g.bowl and g.bowl["mode"] == "cheese", "rubbing up and down on the grater gives grated cheese")
step(g, P(), 0.8)
n0 = len(g.toppings)
sweep(g, 1)
check(len(g.toppings) > n0 + 6, f"cheese is sprinkled where the hand moves ({len(g.toppings) - n0} bits)")

print("mushrooms: knife")
check(set(KINDS) == {"tomato", "cheese", "salami", "mushroom"}, f"for now just 4 ingredients ({KINDS})")
pick(g, "mushroom")
take(g)
for _ in range(WORK["knife"] - 1):
    stroke(g)
shot(g, "pizza_cutting_mushroom")
stroke(g)
step(g, P(), 0.8)
for k in range(3):
    put_piece(g, (cx - 80 + k * 80, cy + 60))
check({t[0] for t in g.toppings} == {"salami", "cheese", "mushroom"}, f"salami, cheese and mushrooms on the pizza ({sorted({t[0] for t in g.toppings})}, item={g.item}, bowl={g.bowl and g.bowl['mode']})")
shot(g, "pizza_decorated")

print("no automatic oven, then into the oven, bake, slice, eat")
step(g, P((W / 2, H * 0.95)), 200)
check(g.phase == "decorate", "the oven never comes by itself - only with the button")
step(g, P(g.oven.c), 1.5)
check(g.phase == "to_oven", "oven button (top right, like 'play again'): the stone oven comes")
step(g, P(), 0.8)
(px, py), _ = g._pizza_pos()
step(g, P((px, py)), 0.2)                            # only a touch ...
step(g, P(), 15.0)                                   # ... and waiting: nothing slides by itself
check(g.phase == "to_oven" and g.push < 0.05, f"the pizza does not go in by itself ({g.phase}, {g.push:.2f})")
shot(g, "pizza_push_hint")


def push(g, frames, start_dx=-60, step_px=7):
    """A hand on the pizza (left part) moving steadily towards the oven."""
    (px, py), _ = g._pizza_pos()
    for i in range(frames):
        g.update(1 / 30, P((px + start_dx + step_px * i, py)))


x0 = g._pizza_pos()[0][0]
push(g, 18)                                          # the hand moves 126 px
half, moved = g.push, g._pizza_pos()[0][0] - x0
check(80 < moved < 140 and g.phase == "to_oven", f"the hand on the pizza takes it along towards the oven ({moved:.0f} px)")
step(g, P((W / 2, H * 0.95)), 2.0)                   # let go halfway
check(abs(g.push - half) < 1e-6, "let go: the pizza stays where it is (no sliding, no sliding back)")
push(g, 50)
check(g.phase == "bake", f"pushed again: it goes into the oven ({g.phase}, {g.push:.2f})")
step(g, P(), BAKE_TIME / 2)
shot(g, "pizza_bake")
step(g, P(), BAKE_TIME / 2 + 0.1)
check(g.phase == "out", "after baking the pizza comes out")
step(g, P(), 1.1)
check(g.phase == "slice", "then it is cut into slices")
step(g, P(), 0.75)
shot(g, "pizza_cutter")
step(g, P(), 1.65)
check(g.phase == "eat", "then the customer comes")
step(g, P(), 1.7)
shot(g, "pizza_eat")
step(g, P(), 1.2)
shot(g, "pizza_yum")
check(g.eaten == 1, "the customer takes one slice")
step(g, P(), 3.0)
check(g.state == "result" and g.stars >= 3, f"result with stars ({g.state}, {g.stars})")
step(g, P(), 1.0)
shot(g, "pizza_result")

print("limits and edge cases")
g2 = PizzaGame(ctx)
step(g2, P(), 3.0)
step(g2, P(g2.oven.c), 2.0)
check(g2.phase == "decorate", "oven with an empty pizza does nothing")
for _ in range(MAX_TOPPINGS + 20):
    g2._place("olive", (g2.center[0], g2.center[1]))
check(len(g2.toppings) == MAX_TOPPINGS, f"topping count is capped at {MAX_TOPPINGS}")
g2.restart()
check(g2.state == "intro" and not g2.toppings, "restart gives a fresh pizza")

print("\n%d Fehler" % len(FAILS))
sys.exit(1 if FAILS else 0)
