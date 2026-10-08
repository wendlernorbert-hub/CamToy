"""Who is the player? One child plays alone; a parent or sibling in view must not take over.

Aufruf:  python tests/test_player.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from minigames.pose import LM, PRESETS, PlayerPicker, child_score, make_players, make_skeleton  # noqa: E402

FAILS = []
W, H = 1280, 720
HEAD = ("nose", "l_eye", "r_eye", "l_ear", "r_ear", "mouth_l", "mouth_r")


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def body(cx, s, head):
    """A skeleton at x = cx, of size s; head = head width relative to the standard figure
    (a 3-4 year old has a big head for its shoulders: ~1.25, an adult ~0.85)."""
    lm = make_skeleton(PRESETS["stand"], cx=cx, s=s, aspect=W / H)
    nose = lm[LM["nose"], :2].copy()
    for n in HEAD:
        lm[LM[n], :2] = nose + (lm[LM[n], :2] - nose) * head
    return lm


child = body(0.35, 0.8, 1.25)
adult = body(0.7, 0.8, 0.85)
far_adult = body(0.7, 0.45, 0.85)          # further back: smaller in the picture than the child

print("child_score")
check(child_score(child) > child_score(adult) + 0.1, "the child looks more child-like than the adult")
check(child_score(child) > child_score(far_adult),
      "an adult further back (smaller in the picture) is still not taken for the child")

DT = 1 / 30


def run(picker, people, seconds):
    out = []
    for _ in range(int(round(seconds / DT))):
        out = picker.update(people, DT)
    return out


print("picking and keeping the player")
pk = PlayerPicker()
got = run(pk, [(0, adult), (1, child)], 0.1)
check(got and got[0][0] == 1, "child and adult in view: the child is the player")
pose = make_players(got, W, H)
xs = [x for x, _ in pose.hand_points()]
check(xs and all(x < W * 0.55 for x in xs), "only the child's hands count (the adult's are ignored)")

pk = PlayerPicker()
run(pk, [(0, child)], 1.0)
got = run(pk, [(0, child), (1, far_adult)], 5.0)
check(got[0][0] == 0, "an adult walking into view does not take over")

pk = PlayerPicker()
run(pk, [(0, child), (1, adult)], 1.0)
got = run(pk, [(1, adult)], 0.3)
check(got == [], "the child gone for a moment: nobody plays (the adult is not handed the game)")
got = run(pk, [(1, adult)], 1.0)
check(got and got[0][0] == 1, "the child gone for good: whoever is left can play")
got = run(pk, [(1, adult), (2, child)], 0.5)
check(got[0][0] == 1, "the child is back: no hectic switch right away")
got = run(pk, [(1, adult), (2, child)], 2.5)
check(got[0][0] == 2, "after a moment the child is the player again")

pk = PlayerPicker()
check(run(pk, [], 0.5) == [], "nobody in view: no player")
lone = body(0.5, 0.8, 0.85)
got = run(pk, [(0, lone)], 0.1)
check(got and got[0][0] == 0, "only one person (e.g. a parent trying it out): that person plays")
half = lone.copy()
half[LM["l_sh"], 2] = half[LM["r_sh"], 2] = 0.0          # shoulders not seen
check(child_score(half) is None, "no shoulders seen: no guess")
check(np.isfinite(child_score(child)), "score is a number")

print()
print("FEHLER:" if FAILS else "Alles in Ordnung.", *FAILS, sep="\n  ")
sys.exit(1 if FAILS else 0)
