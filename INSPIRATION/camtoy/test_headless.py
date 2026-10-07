"""Automatischer Test ohne Kamera/Fenster: simulierte Posen -> Erkennung -> Spiele.

Aufruf:  python test_headless.py [ausgabeordner]
Schreibt Screenshots in den Ausgabeordner (Standard: ./test_out).
"""
import math
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np  # noqa: E402
import pygame  # noqa: E402

import animals  # noqa: E402
from animals import AnimalGame, HOLD, Measures, make_task, trainer_vec  # noqa: E402
from bubbles import BubbleGame  # noqa: E402
from common import Ctx, Sounds, Speaker  # noqa: E402
from dressup import DressUpGame  # noqa: E402
from kungfu import KungFuGame  # noqa: E402
from main import Menu, cutout_surface, to_surface  # noqa: E402
from pose import LM, PRESETS, Pose, make_skeleton  # noqa: E402
from tracker import MockTracker  # noqa: E402

W, H = 960, 720
ASP = W / H
OUT = sys.argv[1] if len(sys.argv) > 1 else "test_out"
os.makedirs(OUT, exist_ok=True)
FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def P(vec, hand=None, both=False):
    lm = make_skeleton(vec, aspect=ASP)
    if hand:
        for n in (("r_wr", "r_idx") + (("l_wr", "l_idx") if both else ())):
            lm[LM[n], 0], lm[LM[n], 1] = hand[0] / W, hand[1] / H
    return Pose(lm, W, H)


pygame.init()
screen = pygame.display.set_mode((W, H))
tracker = MockTracker(ASP)
ctx = Ctx(W, H, Sounds(True), Speaker(False), tracker, tempfile.mkdtemp())
ctx.has_mask = False
cam = to_surface(tracker.latest()[1], (W, H))
STAND = PRESETS["stand"]


def shot(game, pose, name, mask=False):
    screen.blit(cam, (0, 0))
    ctx.has_mask = False
    person = None
    if mask and pose is not None:
        m = np.zeros((tracker.size[1], tracker.size[0]), np.float32)
        yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
        sh = pose.mid("l_sh", "r_sh") * (m.shape[1] / W)
        hp = pose.mid("l_hip", "r_hip") * (m.shape[1] / W)
        body = ((np.abs(xx - sh[0]) < 38) & (yy > sh[1] - 5) & (yy < hp[1] + 120))
        head = ((xx - pose.P("nose")[0] * m.shape[1] / W) ** 2 + (yy - pose.P("nose")[1] * m.shape[1] / W) ** 2) < 40 ** 2
        m[body | head] = 1.0
        person = cutout_surface(tracker.latest()[1], m, (W, H))
        ctx.has_mask = True
    game.draw_back(screen, pose)
    if person is not None:
        screen.blit(person, (0, 0))
    game.draw(screen, pose)
    pygame.image.save(screen, os.path.join(OUT, name + ".png"))


def step(game, pose, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        game.update(dt, pose)


# ------------------------------------------------------------ Aufgaben ---
print("Aufgaben-Erkennung")
HOLDS = {"baum": "baum", "storch": "storch", "schmetterling": "schmetterling", "hase": "hase"}
for lv in (1, 2, 3):
    for key, preset in HOLDS.items():
        task = make_task(key, lv)
        pose = P(PRESETS[preset])
        done = False
        for _ in range(int((HOLD[lv] + 1.0) * 30)):
            prog, match, back = task.update(pose, Measures(pose), 1 / 30)
            done = done or prog >= 1.0
        check(done, f"Level {lv}: {key} wird erkannt")
    # Verwechslungen: Pose A darf Aufgabe B nicht lösen
    for key in HOLDS:
        for other, preset in HOLDS.items():
            if other == key or (key, other) in (("storch", "baum"),):
                continue
            task = make_task(key, lv)
            pose = P(PRESETS[preset])
            m = Measures(pose)
            hit = any(task.update(pose, m, 1 / 30)[1] for _ in range(5))
            if hit and key != "storch":
                check(False, f"Level {lv}: Pose '{preset}' löst fälschlich '{key}' aus")
    for key in HOLDS:
        task = make_task(key, lv)
        pose = P(STAND)
        m = Measures(pose)
        check(not any(task.update(pose, m, 1 / 30)[1] for _ in range(60)), f"Level {lv}: Stehen löst '{key}' nicht aus")

for lv in (1, 2, 3):
    # Frosch (Kniebeuge) und Stern (Hampelmann): hin- und herwechseln
    for key, preset in (("frosch", "frosch"), ("stern", "stern")):
        task = make_task(key, lv)
        total = 0
        t = 0.0
        for i in range(int(1.0 * 30)):
            task.update(P(STAND), Measures(P(STAND)), 1 / 30)
        for i in range(int(task.need * 2.6 * 30) + 60):
            t += 1 / 30
            k = 0.5 - 0.5 * math.cos(2 * math.pi * t / 1.8)
            vec = [a + (b - a) * k for a, b in zip(STAND, PRESETS[preset])]
            p = P(vec)
            task.update(p, Measures(p), 1 / 30)
        check(task.progress >= 1.0, f"Level {lv}: {key} zählt {task.need} Wiederholungen (Zähler {task.count})")
        t2 = make_task(key, lv)
        for i in range(150):
            t2.update(P(STAND), Measures(P(STAND)), 1 / 30)
        check(t2.count == 0, f"Level {lv}: {key} zählt nichts beim Stehen")
    task = make_task("windmuehle", lv)
    for i in range(int(8 * 30)):
        p = P(trainer_vec("windmuehle", i / 30))
        task.update(p, Measures(p), 1 / 30)
    check(task.progress >= 1.0, f"Level {lv}: Windmühle erkannt (Fortschritt {task.progress:.2f})")
    task = make_task("windmuehle", lv)
    for i in range(300):
        task.update(P(STAND), Measures(P(STAND)), 1 / 30)
    check(task.progress == 0.0, f"Level {lv}: Windmühle zählt nichts beim Stehen")

# ------------------------------------------------------------ Seifenblasen ---
print("Seifenblasen")
for lv in (1, 3):
    ctx.level = lv
    g = BubbleGame(ctx)
    step(g, P(STAND), 3.0)
    check(g.state == "play", "Intro geht ins Spiel über")
    step(g, P(STAND), 4.0)
    for _ in range(40):
        if not g.bubbles:
            step(g, P(STAND), 0.3)
            continue
        b = g.bubbles[0]
        g.update(1 / 30, P(STAND, hand=(b.x, b.y)))
    check(g.score >= 5, f"Level {lv}: Blasen platzen mit Hand (Score {g.score})")
    step(g, P(STAND), g.DURATION)
    check(g.state == "result" and g.stars >= 1, f"Level {lv}: Runde endet mit Ergebnis ({g.stars} Sterne)")
ctx.level = 1
g = BubbleGame(ctx)
step(g, P(STAND), 9.0)
shot(g, P(STAND, hand=(480, 300)), "bubbles")
step(g, P(STAND), 40)
shot(g, P(STAND), "bubbles_result")

# ------------------------------------------------------------ Kung-Fu ---
print("Kung-Fu")
for lv in (1, 2, 3):
    ctx.level = lv
    g = KungFuGame(ctx)
    step(g, P(STAND), 3.0)
    for i in range(60 * 30 // 2):
        tg = [t for t in g.targets if not t.hit and t.age > 0.35]
        if tg:
            t0 = tg[0]
            # schneller Schlag durch das Ziel
            for k in range(6):
                x = t0.x + (k - 3) * 40
                g.update(1 / 30, P(STAND, hand=(x, t0.y)))
        else:
            g.update(1 / 30, P(STAND))
        if g.state != "play":
            break
    check(g.score >= 5, f"Level {lv}: Treffer mit schneller Hand (Score {g.score})")
    # langsame Hand (max. 100 px/s) darf auf Level 3 nichts treffen
    if lv == 3:
        g2 = KungFuGame(ctx)
        step(g2, P(STAND), 3.0)
        for i in range(12 * 30):
            x = 480 + 450 * math.sin(0.22 * i / 30)
            g2.update(1 / 30, P(STAND, hand=(x, 300)))
        check(g2.score == 0, f"Level 3: langsame Hand trifft nicht (Score {g2.score})")
ctx.level = 2
g = KungFuGame(ctx)
step(g, P(STAND), 3.0)
step(g, P(STAND), 4.0)
shot(g, P(STAND, hand=(480, 300)), "kungfu")
g.score = 20
g.finish(4)
step(g, P(STAND), 1.5)
shot(g, P(STAND), "kungfu_result")

# ------------------------------------------------------------ Verkleiden ---
print("Verkleiden")
g = DressUpGame(ctx)
for i, tile in enumerate(g.tiles):
    for _ in range(40):
        g.update(1 / 30, P(STAND, hand=tile.c))
    step(g, P(STAND), 0.3)
check(all(v == 1 for v in g.sel.values()), f"Jede Kachel schaltet ein Teil weiter {g.sel}")
step(g, P(STAND), 0.5)
shot(g, P(STAND), "dressup1")
for i, tile in enumerate(g.tiles):
    for _ in range(40 * 2):
        g.update(1 / 30, P(STAND, hand=tile.c))
        if g.sel[list(g.sel)[i]] != 1 and False:
            break
    step(g, P(STAND), 0.3)
print("  Auswahl jetzt:", g.sel)
shot(g, P(STAND), "dressup_mask", mask=True)
shot(g, P(STAND), "dressup_nomask")
for _ in range(45):
    g.update(1 / 30, P(STAND, hand=g.btn_photo.c))
step(g, P(STAND), 0.2)
check(g.countdown is not None, "Foto-Knopf startet Countdown")
shot(g, P(STAND), "dressup_countdown")
step(g, P(STAND), 3.3)
g.draw(screen, P(STAND))
fotos = os.listdir(os.path.join(ctx.out_dir, "fotos")) if os.path.exists(os.path.join(ctx.out_dir, "fotos")) else []
check(len(fotos) == 1, f"Foto gespeichert ({fotos})")

# ------------------------------------------------------------ Tier-Yoga ---
print("Tier-Yoga")
PRES = {"baum": "baum", "storch": "storch", "frosch": "frosch", "stern": "stern",
        "schmetterling": "schmetterling", "hase": "hase", "windmuehle": "stand"}
for lv in (1, 2, 3):
    ctx.level = lv
    g = AnimalGame(ctx)
    step(g, P(STAND), 3.0)
    t_sim = 0.0
    for _ in range(60 * 30):
        if g.state != "play":
            break
        key = g.order[min(g.idx, g.N - 1)]
        t_sim += 1 / 30
        if g.phase != "do":
            p = P(STAND)
        elif key in ("frosch", "stern"):
            k = 0.5 - 0.5 * math.cos(2 * math.pi * t_sim / 1.8)
            p = P([a + (b - a) * k for a, b in zip(STAND, PRESETS[PRES[key]])])
        elif key == "windmuehle":
            p = P(trainer_vec("windmuehle", t_sim))
        else:
            p = P(PRESETS[PRES[key]])
        g.update(1 / 30, p)
    check(g.state == "result" and all(e == 3 for e in g.earned),
          f"Level {lv}: alle 5 Tiere geschafft ({g.earned}), Sterne {g.stars}")
ctx.level = 1
g = AnimalGame(ctx)
g.order[0] = "storch"
g.begin_task()
step(g, P(STAND), 2.5)
step(g, P(PRESETS["storch"]), 0.8)
shot(g, P(PRESETS["storch"]), "animals_storch")
g = AnimalGame(ctx)
g.order[0] = "windmuehle"
g.begin_task()
step(g, P(STAND), 1.0)
shot(g, P(STAND), "animals_intro")
g = AnimalGame(ctx)
step(g, P(STAND), 2.0)
g.finish(4)
g.earned = [3, 3, 2, 3, 1]
step(g, P(STAND), 2.5)
shot(g, P(STAND), "animals_result")

# Menü
menu = Menu(ctx)
screen.blit(cam, (0, 0))
menu.draw(screen, P(STAND))
pygame.image.save(screen, os.path.join(OUT, "menu.png"))
sel = None
for _ in range(60):
    sel = menu.update(1 / 30, P(STAND, hand=menu.tiles[2].c)) or sel
check(sel == 2, "Menü: Hand auf Kachel wählt das Spiel")

# Trainer-Figuren als Übersicht
sheet = pygame.Surface((W, 330))
sheet.fill((200, 215, 240))
from pose import draw_figure  # noqa: E402
for i, key in enumerate(list(animals.INFO)):
    r = pygame.Rect(10 + i * 135, 10, 130, 310)
    pygame.draw.rect(sheet, (255, 255, 255), r, border_radius=10)
    draw_figure(sheet, make_skeleton(trainer_vec(key, 1.3), aspect=ASP, s=0.66), r.inflate(-10, -10), ASP)
pygame.image.save(sheet, os.path.join(OUT, "trainer.png"))

print("\n%d Fehler" % len(FAILS))
sys.exit(1 if FAILS else 0)
