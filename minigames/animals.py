"""Spiel 3: Tier-Yoga - Tiere und Bewegungen nachmachen (Baum, Storch, Frosch, ...).

Pro Runde 5 zufällige Aufgaben. Eine Trainer-Figur macht die Pose vor; die Erkennung
vergleicht Armrichtungen und Körperhöhe (in Rumpfeinheiten, daher unabhängig vom
Abstand zur Kamera). Nie "Game Over": Wer es nicht schafft, bekommt trotzdem einen Stern.
"""
import math
import random

import numpy as np
import pygame

import gfx
from .common import (Game, button_sprite, draw_star, draw_stars_row, draw_timer, ease_out_back,
                     ellipse_pts, progress_ring, star_sprite)
from .pose import PRESETS, draw_figure, lerp_vec, make_skeleton

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
FLAPS = {1: 3, 2: 5, 3: 6}                 # butterfly wing beats
TIMEOUT = {1: 18.0, 2: 14.0, 3: 11.0}      # seconds per animal, then "failed" and on to the next


class Measures:
    """Kennzahlen: Armvektoren in Rumpfeinheiten (ox = nach außen, oy = nach unten)."""

    def __init__(self, pose):
        self.pose = pose
        self.SW = max(pose.shoulder_w(), 1.0)
        # body unit from the shoulders only: sitting close to the camera, the hips are usually out of
        # view or detected in the wrong place, which made every threshold wrong (play-test: Stern)
        self.T = 1.4 * self.SW
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

    # Close to the camera, raised hands leave the picture at the top. Then the elbow decides.
    def arm_up(self, s, thr):
        """Hand at least -thr torso lengths above the shoulder (or, hand unseen, elbow raised)."""
        p, sh = self.pose, self.pose.P(f"{s}_sh")
        if p.vis(f"{s}_wr") >= 0.4:
            return (p.P(f"{s}_wr")[1] - sh[1]) / self.T < thr
        if p.vis(f"{s}_el") >= 0.4:
            return (p.P(f"{s}_el")[1] - sh[1]) / self.T < min(0.0, thr * 0.5)
        return False

    def arm_down(self, s):
        """Hand clearly below the shoulder - or out of the picture at the bottom."""
        p, sh = self.pose, self.pose.P(f"{s}_sh")
        if p.vis(f"{s}_wr") >= 0.4:
            return (p.P(f"{s}_wr")[1] - sh[1]) / self.T > 0.15
        return p.vis(f"{s}_el") < 0.4 or (p.P(f"{s}_el")[1] - sh[1]) / self.T > 0.1

    def arm_vec(self, s):
        """Shoulder -> hand in torso lengths, or None. Hand out of view: estimated from the elbow
        (a stretched arm reaches about twice as far as the elbow)."""
        p = self.pose
        for j, min_len, k in (("wr", 0.4, 1.0), ("el", 0.22, 1.9)):
            if p.vis(f"{s}_{j}") >= 0.4:
                v = (p.P(f"{s}_{j}") - p.P(f"{s}_sh")) / self.T
                if float(np.hypot(*v)) >= min_len:
                    return v * k
        return None


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


class Bob:
    """Counts up-and-down movements of one value (screen y, bigger = lower), relative to where
    it just was - not to a fixed height, so it does not matter how high someone sits or stands.
    A rep = down by at least `down` from the last high point, then up again by `up`."""

    def __init__(self, down, up):
        self.down, self.up = down, up
        self.state, self.top, self.bottom = "up", None, None
        self.depth = 0.0                      # 0..1 how far the current move down has come

    def update(self, v):
        """Returns True when a full down-and-up was completed."""
        if self.top is None:
            self.top = self.bottom = v
            return False
        if self.state == "up":
            self.top = min(self.top, v)
            self.depth = min(1.0, max(0.0, (v - self.top) / self.down))
            if v - self.top >= self.down:
                self.state, self.bottom = "down", v
            return False
        self.bottom = max(self.bottom, v)
        self.depth = 1.0
        if self.bottom - v >= self.up:
            self.state, self.top = "up", v
            return True
        return False


class RepTask:
    kind = "reps"

    def __init__(self, key, level):
        self.key, self.level = key, level
        self.need = FLAPS[level] if key == "schmetterling" else REPS[level]
        self.count, self.match = 0, False
        self.progress = 0.0
        self.state = None
        self.bob, self.sw, self.last_y = None, None, None
        self.timer = 0.0
        self.idle = 0.0
        self.acc = {"l": 0.0, "r": 0.0}
        self.prev = {"l": None, "r": None}

    def update(self, pose, m, dt):
        getattr(self, "_" + self.key)(pose, m, dt)
        return self.progress, self.match, False

    def _frosch(self, pose, m, dt):             # Kniebeuge: the shoulders bob down and up
        # unit: shoulder width (the hips drop out of view when squatting); a small bob is enough
        if self.bob is None:
            self.bob = Bob(*{1: (0.14, 0.08), 2: (0.22, 0.12), 3: (0.3, 0.18)}[self.level])
        sw = self.sw = m.SW if self.sw is None else self.sw + (m.SW - self.sw) * 0.05   # calm unit
        if self.bob.update(float(pose.mid("l_sh", "r_sh")[1]) / sw):
            self.count += 1
            self.rep_event = True
        self.match = self.bob.state == "down"
        part = 0.5 * self.bob.depth if self.bob.state == "up" else 0.6
        self.progress = min(1.0, (self.count + part * (self.count < self.need)) / self.need)

    def _stern(self, pose, m, dt):              # Hampelmann: arms swing down and up again
        # every clear down-and-up of the arms counts (relative, like Frosch). Level 1: the higher
        # arm is enough, else the lower one must move too. Hand out of view: the elbow is used;
        # nothing seen at all: the arms are where they were last (out of the top) or hanging down.
        if self.bob is None:
            self.bob = Bob(*{1: (0.45, 0.4), 2: (0.7, 0.6), 3: (0.9, 0.8)}[self.level])
        ys = [float(v[1]) for v in (m.arm_vec("l"), m.arm_vec("r")) if v is not None]
        if ys:
            y = min(ys) if self.level == 1 else max(ys)
        else:
            y = self.last_y if self.last_y is not None and self.last_y < 0.3 else 1.0
        self.last_y = y
        if self.bob.update(y):
            self.count += 1
            self.rep_event = True
        self.match = y < 0.0                     # arms above the shoulders
        self.progress = min(1.0, (self.count + 0.4 * self.bob.depth * (self.count < self.need)) / self.need)

    def _schmetterling(self, pose, m, dt):     # Flügel schlagen: arms move up and down
        # any clear up-and-down of the arms counts, at whatever height (the hand may be out of the
        # picture - then the elbow is used); arms only need to be a little away from the body
        if self.bob is None:
            self.bob = Bob(*{1: (0.18, 0.14), 2: (0.25, 0.2), 3: (0.32, 0.26)}[self.level])
        out = {1: 0.1, 2: 0.2, 3: 0.3}[self.level]
        ys = []
        for s, sign in (("l", -1), ("r", 1)):
            v = m.arm_vec(s)
            if v is not None and float(v[0]) * sign > out:
                ys.append(float(v[1]))
        if len(ys) < (1 if self.level == 1 else 2):
            self.match = False
            return
        # one wing beat = arms up and down again (value: how high the arms are)
        if self.bob.update(-sum(ys) / len(ys)):
            self.count += 1
            self.rep_event = True
        self.match = True
        self.progress = min(1.0, (self.count + 0.4 * self.bob.depth * (self.count < self.need)) / self.need)

    def _windmuehle(self, pose, m, dt):        # Arme kreisen
        moving = False
        for s in "lr":
            v = m.arm_vec(s)                      # the elbow takes over when the hand is out of view
            if v is None:
                self.prev[s] = None
                continue
            ang = math.atan2(v[1], v[0])
            if self.prev[s] is not None:
                d = (ang - self.prev[s] + math.pi) % (2 * math.pi) - math.pi
                if abs(d) < 1.6:                  # ignore jumps (hand <-> elbow switch, glitches)
                    self.acc[s] += d
                    moving = moving or abs(d) > 0.02
            self.prev[s] = ang
        self.idle = 0.0 if moving else self.idle + dt
        if self.idle > 2.5:                       # a long stop slowly loses what was turned
            for s in "lr":
                self.acc[s] *= math.exp(-dt)
        circles = max(abs(self.acc["l"]), abs(self.acc["r"])) / (2 * math.pi)
        need = {1: 0.6, 2: 1.0, 3: 1.6}[self.level]
        self.match = moving
        self.progress = min(1.0, circles / need)


INFO = {
    "baum": ("Baum", "Mach den Baum! Strecke die Arme hoch.", pic_baum),
    "frosch": ("Frosch", "Mach den Frosch! Geh in die Hocke.", pic_frosch),
    "stern": ("Stern", "Mach den Stern! Arme hoch und runter.", pic_stern),
    "schmetterling": ("Schmetterling", "Mach den Schmetterling! Flieg mit den Armen.", pic_schmetterling),
    "hase": ("Hase", "Mach den Hasen! Hände wie Hasenohren.", pic_hase),
    "windmuehle": ("Windmühle", "Mach die Windmühle! Dreh die Arme im Kreis.", pic_windmuehle),
}


def make_task(key, level):
    if key == "baum":
        return HoldTask(key, level, chk_baum)
    if key == "hase":
        return HoldTask(key, level, chk_hase)
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
    if key == "schmetterling":                  # arms out to the sides, flapping up and down
        v = list(PRESETS["schmetterling"])
        dy = 0.0 + 0.12 * math.sin(2 * math.pi * t / 0.8)
        v[1] = v[3] = dy
        return v
    pose = PRESETS[key]
    period = {"frosch": 2.4, "stern": 1.6}.get(key, 3.4)
    u = (t % period) / period
    if key in ("frosch", "stern"):
        k = 0.5 - 0.5 * math.cos(2 * math.pi * u)
    else:                                   # rein, halten, raus
        k = min(1.0, u / 0.2) if u < 0.7 else max(0.0, 1 - (u - 0.7) / 0.2)
        k = k * k * (3 - 2 * k)
    return lerp_vec(stand, pose, k)


# ------------------------------------------------------------------ Grafik ---

ANIM_PERIOD = {"windmuehle": 2 * math.pi / 2.2, "schmetterling": 2 * math.pi / 6, "stern": math.pi}
ANIM_FRAMES = 16


def animal_sprite(key, t):
    """Polished animal picture; moving ones (windmill, butterfly, star) cycle through cached frames."""
    pic = INFO[key][2]
    period = ANIM_PERIOD.get(key)
    f = int(t / period * ANIM_FRAMES) % ANIM_FRAMES if period else 0
    tt = f / ANIM_FRAMES * period if period else 0.0
    return gfx.cached(("animal", key, f), lambda: gfx.icon_sprite(lambda s, c, r: pic(s, c, r, tt), 64,
                                                                  pad=1.3, outline=4, depth=0.2))




def _panel(size):
    def build():
        s = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 255, 255, 150), s.get_rect(), border_radius=28)
        pygame.draw.rect(s, (255, 255, 255, 230), s.get_rect(), 5, border_radius=28)
        return gfx.sticker(s, 0, shadow=70, offset=(0, 6), blur=6)
    return gfx.cached(("ypanel", tuple(size)), build)


def _sad(surf, c, r):
    x, y = c
    ink = (40, 50, 90)
    pygame.draw.circle(surf, (170, 180, 225), c, int(r))
    for sx in (-1, 1):
        pygame.draw.circle(surf, ink, (int(x + sx * r * .36), int(y - r * .18)), max(2, int(r * .09)))
        pygame.draw.line(surf, ink, (x + sx * r * .55, y - r * .32), (x + sx * r * .2, y - r * .46),
                         max(2, int(r * .06)))                                # inner ends up = sad
    pygame.draw.arc(surf, ink, (x - r * .45, y + r * .2, r * .9, r * .6), math.radians(30), math.radians(150),
                    max(3, int(r * .08)))
    pygame.draw.circle(surf, (120, 190, 255), (int(x + r * .58), int(y + r * .05)), max(2, int(r * .09)))   # a tear


# ---------------------------------------------------------------------- Spiel ---

class AnimalGame(Game):
    title = "Tier-Yoga"
    speech = "Mach die Tiere nach!"
    N = 5

    @staticmethod
    def icon(surf, c, r):
        """The trainer figure that shows the poses, doing a happy star jump."""
        rect = pygame.Rect(0, 0, int(r * 2.3), int(r * 2.4))
        rect.center = (int(c[0]), int(c[1]))
        draw_figure(surf, make_skeleton(PRESETS["stern"], aspect=1.0, s=0.74), rect, 1.0, y0=0.1, y1=0.99)

    def on_restart(self):
        self.order = random.sample(list(INFO), self.N)
        self.idx, self.earned = 0, []
        self.begin_task()

    def begin_task(self):
        key = self.order[self.idx]
        self.task = make_task(key, self.ctx.level)
        self.tasks = {}                  # one task per person (slot): whoever does it best counts
        self.phase, self.ptime = "show", 0.0
        self.ctx.log("task", animal=key)
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
        prog, match, back = 0.0, False, True
        for p in (pose.all if pose else []):
            if not p.ok:
                continue
            task = self.tasks.get(p.slot)
            if task is None:
                task = self.tasks[p.slot] = make_task(self.order[self.idx], self.ctx.level)
                task.rep_event = False
            pr, mt, bk = task.update(p, Measures(p), dt)
            if pr >= prog:
                prog, self.task = pr, task
            match, back = match or mt, back and bk
            if getattr(task, "rep_event", False):
                task.rep_event = False
                self.ctx.play("quak" if self.order[self.idx] == "frosch" else "good")
                self.particles.burst((self.W / 2, self.H / 2), 14, [(255, 230, 80), (255, 255, 255)], 300, .6, (3, 7), 300, "star")
        self.need_back = back
        if back and not self.said_back and self.ptime > 3:
            self.said_back = True
            self.ctx.say("Geh ein Stück zurück, damit ich dich ganz sehe.")
        self.prog = prog
        if prog >= 1.0:
            self.end_task(3)
        elif self.ptime > TIMEOUT[self.ctx.level]:
            self.end_task(0)                       # time is up: failed, the next animal comes

    def end_task(self, stars):
        """stars: 3 = done, 0 = failed (time ran out)."""
        self.earned.append(stars)
        self.phase, self.ptime = "cheer", 0.0
        self.ctx.log("task_end", animal=self.order[self.idx], stars=stars,
                     progress=round(getattr(self, "prog", 0.0), 2))
        if stars == 0:
            self.ctx.play("down")
            self.ctx.say("Fehlgeschlagen!")
            self.particles.burst((self.W / 2, self.H / 2), 18, [(150, 165, 215), (255, 255, 255)],
                                 220, .7, (4, 9), 500)
            return
        self.ctx.play("chime")
        self.ctx.say("Super!")
        self.particles.confetti(self.W, 40)

    def play_draw(self, surf, pose):
        key = self.order[min(self.idx, self.N - 1)]
        name, _, pic = INFO[key]
        # (no skeleton and no green glow over the player: the ring around the animal shows progress)
        # Tier-Bild links oben mit Fortschrittsring
        c = (130, 200)
        k = ease_out_back(self.ptime / 0.5) if self.phase == "show" else 1.0
        prog = getattr(self, "prog", 0.0) if self.phase == "do" else (
            (1.0 if self.earned[-1] else 0.0) if self.phase == "cheer" else 0.0)
        gfx.blit_center(surf, button_sprite(96, (255, 200, 60)), c, scale=0.6 + 0.4 * k)
        gfx.blit_center(surf, animal_sprite(key, self.t), c, scale=max(0.05, k))
        progress_ring(surf, c, 116, prog, width=14)
        # Trainer
        panel = pygame.Rect(16, 336, 250, 330)
        gfx.blit_center(surf, _panel(panel.size), panel.center)
        asp = self.W / self.H
        draw_figure(surf, make_skeleton(trainer_vec(key, self.t), aspect=asp, s=0.74), panel.inflate(-20, -20), asp)
        # Sterne oben rechts
        if self.phase == "do":                       # shrinking time bar, red for the last seconds
            draw_timer(surf, (self.W / 2, self.H - 34), 360, 1.0 - self.ptime / TIMEOUT[self.ctx.level])
        if self.phase == "cheer":
            k = ease_out_back(self.ptime / 0.4)
            c = (self.W // 2, self.H // 2 - 40)
            if self.earned[-1]:                      # solved: a big gold star pops up
                gfx.blit_center(surf, gfx.sunburst(260), c, scale=k, angle=self.t * 30)
                gfx.blit_center(surf, star_sprite(150), c, scale=max(0.05, k), angle=math.sin(self.t * 4) * 8)
            else:                                    # failed: a sad face (no words needed)
                gfx.blit_center(surf, gfx.cached(("sadface",), lambda: gfx.icon_sprite(_sad, 110, pad=1.2)),
                                c, scale=max(0.05, k))

    def result_draw(self, surf):
        pass                                          # the stars on top say it all
