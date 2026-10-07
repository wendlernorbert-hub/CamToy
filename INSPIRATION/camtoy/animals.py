"""Spiel 3: Tier-Yoga - Tiere und Bewegungen nachmachen (Baum, Storch, Frosch, ...).

Pro Runde 5 zufällige Aufgaben. Eine Trainer-Figur macht die Pose vor; die Erkennung
vergleicht Armrichtungen und Körperhöhe (in Rumpfeinheiten, daher unabhängig vom
Abstand zur Kamera). Nie "Game Over": Wer es nicht schafft, bekommt trotzdem einen Stern.
"""
import math
import random

import numpy as np
import pygame

from common import (Game, circle_alpha, draw_ring, draw_star, draw_stars_row, ellipse_pts,
                    ease_out_back, text)
from pose import BONES, PRESETS, draw_figure, lerp_vec, make_skeleton

# ---------------------------------------------------------------- Tier-Bilder ---


def _el(surf, col, c, rx, ry, rot=0.0, edge=None, w=3):
    pts = ellipse_pts(c[0], c[1], rx, ry, rot, 28)
    pygame.draw.polygon(surf, col, pts)
    if edge:
        pygame.draw.polygon(surf, edge, pts, w)


def pic_baum(surf, c, r, t):
    x, y = c
    pygame.draw.rect(surf, (130, 85, 50), (x - .13 * r, y + .05 * r, .26 * r, .85 * r), border_radius=4)
    for dx, dy, k in ((0, -.4, .6), (-.42, -.05, .45), (.42, -.05, .45), (0, -.1, .5)):
        pygame.draw.circle(surf, (60, 160, 70), (int(x + dx * r), int(y + dy * r)), int(k * r))
    for dx, dy in ((-.2, -.4), (.3, -.15), (-.35, .0), (.1, -.62)):
        pygame.draw.circle(surf, (230, 60, 60), (int(x + dx * r), int(y + dy * r)), int(.09 * r))


def pic_storch(surf, c, r, t):
    x, y = c
    for dx, bend in ((-.05, 0), (.12, .12)):
        pygame.draw.line(surf, (230, 70, 60), (x + dx * r, y + .3 * r), (x + (dx + bend) * r, y + .95 * r), max(3, int(r * .06)))
    _el(surf, (252, 252, 255), (x - .1 * r, y + .02 * r), .52 * r, .3 * r, -.15, (150, 160, 190))
    pygame.draw.line(surf, (252, 252, 255), (x + .28 * r, y - .05 * r), (x + .42 * r, y - .55 * r), max(4, int(r * .15)))
    pygame.draw.circle(surf, (252, 252, 255), (int(x + .45 * r), int(y - .62 * r)), int(.15 * r))
    pygame.draw.polygon(surf, (255, 150, 30), [(x + .56 * r, y - .7 * r), (x + 1.1 * r, y - .6 * r), (x + .56 * r, y - .55 * r)])
    pygame.draw.circle(surf, (20, 20, 30), (int(x + .5 * r), int(y - .66 * r)), max(2, int(.03 * r)))
    _el(surf, (40, 45, 70), (x - .3 * r, y + .0 * r), .32 * r, .15 * r, -.2)


def pic_frosch(surf, c, r, t):
    x, y = c
    _el(surf, (90, 200, 80), (x, y + .15 * r), .85 * r, .6 * r, 0, (40, 120, 40))
    for s in (-1, 1):
        pygame.draw.circle(surf, (90, 200, 80), (int(x + s * .4 * r), int(y - .35 * r)), int(.3 * r))
        pygame.draw.circle(surf, (255, 255, 255), (int(x + s * .4 * r), int(y - .37 * r)), int(.22 * r))
        pygame.draw.circle(surf, (20, 20, 30), (int(x + s * .4 * r), int(y - .35 * r)), int(.11 * r))
        pygame.draw.circle(surf, (255, 150, 160), (int(x + s * .55 * r), int(y + .2 * r)), int(.1 * r))
    pygame.draw.arc(surf, (40, 100, 40), (x - .5 * r, y - .05 * r, r, .6 * r), math.pi * 1.1, math.pi * 1.9, max(3, int(r * .06)))


def pic_stern(surf, c, r, t):
    draw_star(surf, c, r * 1.0, (255, 220, 50), math.sin(t * 2) * .12, (230, 140, 0), .55)
    for s in (-1, 1):
        pygame.draw.circle(surf, (40, 30, 30), (int(c[0] + s * .2 * r), int(c[1] - .05 * r)), max(2, int(.06 * r)))
    pygame.draw.arc(surf, (190, 70, 40), (c[0] - .25 * r, c[1] - .1 * r, .5 * r, .4 * r), math.pi * 1.1, math.pi * 1.9, max(2, int(r * .05)))


def pic_schmetterling(surf, c, r, t):
    x, y = c
    flap = .85 + .15 * math.sin(t * 6)
    for s in (-1, 1):
        _el(surf, (255, 140, 60), (x + s * .5 * r * flap, y - .3 * r), .5 * r * flap, .36 * r, -s * .5, (150, 70, 20))
        _el(surf, (255, 100, 160), (x + s * .38 * r * flap, y + .3 * r), .36 * r * flap, .28 * r, s * .5, (150, 40, 90))
        pygame.draw.circle(surf, (255, 255, 255), (int(x + s * .6 * r * flap), int(y - .35 * r)), int(.08 * r))
        pygame.draw.line(surf, (60, 40, 40), (x + s * .05 * r, y - .45 * r), (x + s * .3 * r, y - .8 * r), 3)
    _el(surf, (60, 40, 50), (x, y), .09 * r, .5 * r)


def pic_hase(surf, c, r, t):
    x, y = c
    for s in (-1, 1):
        _el(surf, (245, 245, 250), (x + s * .24 * r, y - .45 * r), .14 * r, .5 * r, s * .1, (150, 150, 170))
        _el(surf, (255, 170, 190), (x + s * .24 * r, y - .43 * r), .07 * r, .38 * r, s * .1)
    pygame.draw.circle(surf, (245, 245, 250), (int(x), int(y + .25 * r)), int(.55 * r))
    pygame.draw.circle(surf, (150, 150, 170), (int(x), int(y + .25 * r)), int(.55 * r), 3)
    for s in (-1, 1):
        pygame.draw.circle(surf, (30, 30, 40), (int(x + s * .2 * r), int(y + .15 * r)), max(2, int(.06 * r)))
    pygame.draw.circle(surf, (255, 120, 150), (int(x), int(y + .3 * r)), int(.07 * r))
    pygame.draw.rect(surf, (255, 255, 255), (x - .07 * r, y + .4 * r, .14 * r, .14 * r))


def pic_windmuehle(surf, c, r, t):
    x, y = c
    pygame.draw.polygon(surf, (150, 105, 70), [(x - .12 * r, y + .95 * r), (x + .12 * r, y + .95 * r), (x + .05 * r, y), (x - .05 * r, y)])
    cols = [(230, 70, 70), (250, 200, 50), (70, 150, 230), (90, 200, 100)]
    for i in range(4):
        a = t * 2.2 + i * math.pi / 2
        ux, uy = math.cos(a), math.sin(a)
        nx, ny = -uy, ux
        pygame.draw.polygon(surf, cols[i], [(x, y), (x + ux * .9 * r + nx * .05 * r, y + uy * .9 * r + ny * .05 * r),
                                            (x + ux * .9 * r + nx * .3 * r, y + uy * .9 * r + ny * .3 * r),
                                            (x + ux * .3 * r + nx * .3 * r, y + uy * .3 * r + ny * .3 * r)])
    pygame.draw.circle(surf, (60, 60, 80), (int(x), int(y)), int(.1 * r))


# ------------------------------------------------------------------ Aufgaben ---

HOLD = {1: 1.6, 2: 2.2, 3: 3.0}
REPS = {1: 2, 2: 3, 3: 4}
TIMEOUT = {1: 32.0, 2: 28.0, 3: 24.0}


class Measures:
    """Kennzahlen: Armvektoren in Rumpfeinheiten (ox = nach außen, oy = nach unten)."""

    def __init__(self, pose):
        self.pose = pose
        self.T = max(pose.torso(), 1.0)
        self.SW = max(pose.shoulder_w(), 1.0)
        self.arm = {}
        self.wr = {}
        for s, sign in (("l", -1), ("r", 1)):
            if pose.has(f"{s}_sh", f"{s}_wr", thr=0.4):
                v = (pose.P(f"{s}_wr") - pose.P(f"{s}_sh")) / self.T
                self.arm[s] = (float(v[0]) * sign, float(v[1]), float(np.hypot(*v)))
                self.wr[s] = pose.P(f"{s}_wr")
            else:
                self.arm[s] = None

    @property
    def both(self):
        return self.arm["l"] is not None and self.arm["r"] is not None


class HoldTask:
    kind = "hold"

    def __init__(self, key, level, check, needs=()):
        self.key, self.level, self.check, self.needs = key, level, check, needs
        self.progress, self.match = 0.0, False

    def update(self, pose, m, dt):
        if self.needs and not pose.has(*self.needs, thr=0.5):
            self.match = False
            return self.progress, False, True
        self.match = bool(self.check(m, pose, self.level))
        if self.match:
            self.progress = min(1.0, self.progress + dt / HOLD[self.level])
        else:
            self.progress = max(0.0, self.progress - dt * 1.2)
        return self.progress, self.match, False


def chk_baum(m, pose, lv):
    if not m.both:
        return False
    up = {1: -0.55, 2: -0.7, 3: -0.8}[lv]
    spread = {1: 2.3, 2: 2.0, 3: 1.7}[lv]
    straight = {1: 0.78, 2: 0.85, 3: 0.9}[lv]       # gestreckt (Hase hat gebeugte Arme)
    return (m.arm["l"][1] < up and m.arm["r"][1] < up
            and m.arm["l"][2] > straight and m.arm["r"][2] > straight
            and abs(m.wr["l"][0] - m.wr["r"][0]) < spread * m.SW)


def chk_schmetterling(m, pose, lv):
    if not m.both:
        return False
    ox = {1: 0.55, 2: 0.7, 3: 0.8}[lv]
    oy = {1: 0.5, 2: 0.4, 3: 0.3}[lv]
    return all(m.arm[s][0] > ox and abs(m.arm[s][1]) < oy for s in "lr")


def chk_hase(m, pose, lv):
    if not m.both or not pose.has("nose", "l_eye", "r_eye", thr=0.4):
        return False
    eye_y = (pose.P("l_eye")[1] + pose.P("r_eye")[1]) / 2
    nose_x = pose.P("nose")[0]
    near = {1: 1.5, 2: 1.2, 3: 1.0}[lv]
    for s in "lr":
        if m.wr[s][1] > eye_y + 0.1 * m.T or abs(m.wr[s][0] - nose_x) > near * m.SW:
            return False
        if m.arm[s][2] > 1.0:       # Arm gestreckt = Baum, nicht Hase
            return False
    return True


def chk_storch(m, pose, lv):
    leg = float(np.linalg.norm(pose.mid("l_hip", "r_hip") - pose.mid("l_an", "r_an")))
    if leg < 1:
        return False
    lift = abs(pose.P("l_an")[1] - pose.P("r_an")[1]) / leg
    return lift > {1: 0.12, 2: 0.16, 3: 0.22}[lv]


class RepTask:
    kind = "reps"

    def __init__(self, key, level):
        self.key, self.level = key, level
        self.need = REPS[level]
        self.count, self.match = 0, False
        self.progress = 0.0
        self.state = None
        self.buf, self.base = [], None
        self.timer = 0.0
        self.idle = 0.0
        self.acc = {"l": 0.0, "r": 0.0}
        self.prev = {"l": None, "r": None}

    def update(self, pose, m, dt):
        getattr(self, "_" + self.key)(pose, m, dt)
        return self.progress, self.match, False

    def _frosch(self, pose, m, dt):             # Kniebeuge (nur Oberkörper nötig)
        sy = float(pose.mid("l_sh", "r_sh")[1])
        self.timer += dt
        if self.base is None:
            self.buf.append((sy, m.T))
            if self.timer > 0.8:
                ys, ts = zip(*self.buf)
                self.base = (float(np.median(ys)), float(np.median(ts)))
                self.state = "up"
            return
        by, bt = self.base
        drop = (sy - by) / bt
        if drop < -0.05:
            self.base = (by + (sy - by) * 0.2, bt)
        down = {1: 0.22, 2: 0.30, 3: 0.38}[self.level]
        up = 0.10
        if self.state == "up" and drop > down:
            self.state = "down"
        elif self.state == "down" and drop < up:
            self.state = "up"
            self.count += 1
            self.rep_event = True
        self.match = self.state == "down"
        part = min(1.0, max(0.0, drop / down)) * 0.5 if self.state == "up" else \
            0.5 + 0.5 * (1 - min(1.0, max(0.0, (drop - up) / (down - up))))
        self.progress = min(1.0, (self.count + part * (self.count < self.need)) / self.need)

    def _stern(self, pose, m, dt):              # Hampelmann: Arme hoch/runter
        if not m.both:
            return
        oy = (m.arm["l"][1], m.arm["r"][1])
        open_thr = {1: -0.2, 2: -0.35, 3: -0.5}[self.level]
        is_open = max(oy) < open_thr
        is_closed = min(oy) > 0.45
        if self.state is None:
            self.state = "open" if is_open else ("closed" if is_closed else None)
        elif self.state == "closed" and is_open:
            self.state = "open"
            self.count += 1
            self.rep_event = True
        elif self.state == "open" and is_closed:
            self.state = "closed"
        self.match = self.state == "open"
        self.progress = min(1.0, (self.count + (0.4 if self.match else 0)) / self.need)

    def _windmuehle(self, pose, m, dt):        # Arme kreisen
        moving = False
        for s in "lr":
            a = m.arm[s]
            if a is None or a[2] < 0.55:
                self.prev[s] = None
                continue
            v = pose.P(f"{s}_wr") - pose.P(f"{s}_sh")
            ang = math.atan2(v[1], v[0])
            if self.prev[s] is not None:
                d = (ang - self.prev[s] + math.pi) % (2 * math.pi) - math.pi
                self.acc[s] += d
                moving = moving or abs(d) > 0.02
            self.prev[s] = ang
        self.idle = 0.0 if moving else self.idle + dt
        if self.idle > 1.5:
            self.acc = {"l": 0.0, "r": 0.0}
        circles = max(abs(self.acc["l"]), abs(self.acc["r"])) / (2 * math.pi)
        need = {1: 1.5, 2: 2.0, 3: 3.0}[self.level]
        self.match = moving
        self.progress = min(1.0, circles / need)


INFO = {
    "baum": ("Baum", "Mach den Baum! Strecke die Arme hoch.", pic_baum),
    "storch": ("Storch", "Mach den Storch! Steh auf einem Bein.", pic_storch),
    "frosch": ("Frosch", "Mach den Frosch! Geh in die Hocke.", pic_frosch),
    "stern": ("Stern", "Mach den Stern! Arme hoch und runter.", pic_stern),
    "schmetterling": ("Schmetterling", "Mach den Schmetterling! Arme zur Seite.", pic_schmetterling),
    "hase": ("Hase", "Mach den Hasen! Hände wie Hasenohren.", pic_hase),
    "windmuehle": ("Windmühle", "Mach die Windmühle! Dreh die Arme im Kreis.", pic_windmuehle),
}


def make_task(key, level):
    if key == "baum":
        return HoldTask(key, level, chk_baum)
    if key == "schmetterling":
        return HoldTask(key, level, chk_schmetterling)
    if key == "hase":
        return HoldTask(key, level, chk_hase)
    if key == "storch":
        return HoldTask(key, level, chk_storch, needs=("l_hip", "r_hip", "l_an", "r_an"))
    return RepTask(key, level)


def trainer_vec(key, t):
    """Parametervektor der Trainer-Figur zur Zeit t (Sekunden)."""
    stand = PRESETS["stand"]
    if key == "windmuehle":
        a = t * 3.2
        v = list(stand)
        v[0], v[1] = -0.32 * math.cos(a), 0.32 * math.sin(a)
        v[2], v[3] = 0.32 * math.cos(a), 0.32 * math.sin(a)
        return v
    pose = PRESETS[{"storch": "storch"}.get(key, key)]
    period = {"frosch": 2.4, "stern": 1.6}.get(key, 3.4)
    u = (t % period) / period
    if key in ("frosch", "stern"):
        k = 0.5 - 0.5 * math.cos(2 * math.pi * u)
    else:                                   # rein, halten, raus
        k = min(1.0, u / 0.2) if u < 0.7 else max(0.0, 1 - (u - 0.7) / 0.2)
        k = k * k * (3 - 2 * k)
    return lerp_vec(stand, pose, k)


# ---------------------------------------------------------------------- Spiel ---

class AnimalGame(Game):
    title = "Tier-Yoga"
    speech = "Mach die Tiere nach!"
    N = 5

    @staticmethod
    def icon(surf, c, r):
        pic_frosch(surf, (c[0], c[1] - r * .05), r * 1.0, 0)

    def on_restart(self):
        self.order = random.sample(list(INFO), self.N)
        self.idx, self.earned = 0, []
        self.begin_task()

    def begin_task(self):
        key = self.order[self.idx]
        self.task = make_task(key, self.ctx.level)
        self.phase, self.ptime = "show", 0.0
        self.said_back = False
        self.need_back = False
        self.task.rep_event = False
        self.ctx.say(INFO[key][1])

    def play_update(self, dt, pose, hands):
        self.ptime += dt
        if self.phase == "show":
            if self.ptime > 2.2:
                self.phase, self.ptime = "do", 0.0
            return
        if self.phase == "cheer":
            if self.ptime > 1.8:
                self.idx += 1
                if self.idx >= self.N:
                    total = sum(self.earned)
                    self.finish(1 + round(4 * total / (3 * self.N)))
                else:
                    self.begin_task()
            return
        # ---- phase "do"
        prog, match, back = 0.0, False, False
        if pose and pose.ok:
            m = Measures(pose)
            prog, match, back = self.task.update(pose, m, dt)
            if getattr(self.task, "rep_event", False):
                self.task.rep_event = False
                self.ctx.play("good")
                self.particles.burst((self.W / 2, self.H / 2), 14, [(255, 230, 80), (255, 255, 255)], 300, .6, (3, 7), 300, "star")
        else:
            back = True
        self.need_back = back
        if back and not self.said_back and self.ptime > 3:
            self.said_back = True
            self.ctx.say("Geh ein Stück zurück, damit ich dich ganz sehe.")
        self.prog = prog
        if prog >= 1.0:
            self.end_task(3)
        elif self.ptime > TIMEOUT[self.ctx.level]:
            self.end_task(2 if prog > 0.5 else 1)

    def end_task(self, stars):
        self.earned.append(stars)
        self.phase, self.ptime = "cheer", 0.0
        self.ctx.play("chime" if stars == 3 else "good")
        self.ctx.say("Super!" if stars == 3 else "Fast geschafft!")
        self.particles.confetti(self.W, 40 if stars == 3 else 15)

    def _draw_player(self, surf, pose):
        if not pose or not pose.ok:
            return
        col = (90, 255, 130) if (self.phase == "do" and self.task.match) else (255, 255, 255)
        for a, b in BONES:
            if pose.has(a, b, thr=0.4):
                pygame.draw.line(surf, col, pose.P(a), pose.P(b), 7)
        for n in ("l_sh", "r_sh", "l_el", "r_el", "l_wr", "r_wr", "l_hip", "r_hip", "l_kn", "r_kn", "l_an", "r_an"):
            if pose.vis(n) >= 0.4:
                pygame.draw.circle(surf, col, (int(pose.P(n)[0]), int(pose.P(n)[1])), 8)

    def play_draw(self, surf, pose):
        key = self.order[min(self.idx, self.N - 1)]
        name, _, pic = INFO[key]
        if self.state == "play":
            self._draw_player(surf, pose)
        # Tier-Bild links oben mit Fortschrittsring
        c = (125, 195)
        circle_alpha(surf, (255, 255, 255, 170), c, 92)
        k = ease_out_back(self.ptime / 0.5) if self.phase == "show" else 1.0
        pic(surf, c, 62 * max(0.1, k), self.t)
        prog = getattr(self, "prog", 0.0) if self.phase == "do" else (1.0 if self.phase == "cheer" else 0.0)
        pygame.draw.circle(surf, (255, 255, 255), c, 100, 4)
        draw_ring(surf, c, 108, 98, prog, (255, 225, 60))
        # Trainer
        panel = pygame.Rect(16, 318, 250, 330)
        veil = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(veil, (255, 255, 255, 125), veil.get_rect(), border_radius=24)
        surf.blit(veil, panel.topleft)
        asp = self.W / self.H
        draw_figure(surf, make_skeleton(trainer_vec(key, self.t), aspect=asp, s=0.74), panel.inflate(-20, -20), asp)
        text(surf, name, 38, (panel.centerx, panel.bottom + 30))
        # Sterne oben rechts
        draw_stars_row(surf, (self.W - 160, 58), self.N, len(self.earned), 36)
        if self.phase == "do" and self.need_back:
            text(surf, "Geh ein Stück zurück", 46, (self.W // 2, self.H - 60), (255, 240, 140))
        if self.phase == "cheer":
            text(surf, "Super!" if self.earned[-1] == 3 else "Fast!", int(120 * ease_out_back(self.ptime / 0.4)),
                 (self.W // 2, self.H // 2 - 60), (255, 240, 120))

    def result_draw(self, surf):
        text(surf, "%d von %d Tieren geschafft" % (sum(1 for e in self.earned if e == 3), self.N), 44,
             (self.W // 2, self.H * 0.42))
