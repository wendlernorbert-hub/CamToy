"""Spiel 4: Kung-Fu-Meister - das Kind wird zum blauen Ninja und haut rote Ninjas weg.

Whack-a-Mole mit dem Körper. Level 1: einfach berühren. Level 2/3: die Hand muss schnell sein
(echter "Schlag"). Nur Hände zählen - Beine sind vor der Kamera nie im Bild.
Zwischendurch taucht ein Boss-Ninja auf, der mehrere Treffer braucht. Am Ende gibt es einen
Gürtel in Weiß bis Schwarz. Kein Verlieren: ein entkommener Ninja kostet nichts.
"""
import math
import random
from collections import deque

import pygame

import gfx
from .common import (Game, circle_alpha, draw_cursors, draw_stars_row, draw_timer, ease_out_back,
                     ellipse_pts, heart_pts, star_pts, star_sprite)
from .costumes import Xf

LEVELS = {1: dict(life=3.4, n=2, speed=0, every=0.9, r=64),
          2: dict(life=2.5, n=3, speed=260, every=0.7, r=54),
          3: dict(life=1.9, n=3, speed=430, every=0.5, r=46)}
HAND_SPOTS = [(.13, .30), (.87, .30), (.11, .58), (.89, .58), (.22, .17), (.78, .17),
              (.21, .44), (.79, .44), (.30, .27), (.70, .27)]
# boss ninja: hits needed, seconds on screen, kills of normal ninjas between two bosses
BOSS = {1: dict(hp=3, life=9.0, every=8), 2: dict(hp=4, life=8.0, every=7), 3: dict(hp=5, life=7.0, every=6)}
BOSS_SIZE = 1.65               # boss radius = normal radius * this
BOSS_MIN_SPEED = 150.0         # px/s: even on level 1 the boss needs a real swing
BOSS_COOLDOWN = 0.55           # seconds between two hits that count (one swing = one hit)
BOSS_KILL_POINTS = 5
# fire fist flame colours (colour, glow power): young/hot -> old/dark, and the core of a fast hand
FIRE = (((255, 190, 70), 0.45), ((255, 100, 15), 0.45), ((170, 30, 5), 0.4))
FIRE_CORE = (((255, 90, 10), 0.75), ((255, 225, 150), 0.6))
BLUE = (60, 130, 240)
BLUE_DARK = (30, 70, 170)
BELTS = [(0, (245, 245, 245), "Weißer Gürtel"), (4, (250, 220, 60), "Gelber Gürtel"),
         (8, (250, 150, 40), "Oranger Gürtel"), (13, (80, 190, 90), "Grüner Gürtel"),
         (18, (70, 130, 230), "Blauer Gürtel"), (24, (140, 90, 50), "Brauner Gürtel"),
         (30, (35, 35, 40), "Schwarzer Gürtel")]


def belt_index(score):
    return max(i for i, (need, _, _) in enumerate(BELTS) if score >= need)


def draw_ninja(surf, c, r, t, style="red", flash=0.0, fangs=True, face=True):
    """Enemy ninja. style: "red" (normal) or "boss" (crimson, golden band, horns).
    face=False: hood, horns and band only - the boss's face is drawn separately per damage stage."""
    x, y = c
    boss = style == "boss"
    hood = (135, 22, 42) if boss else (212, 48, 58)
    edge = (60, 10, 22) if boss else (110, 20, 32)
    band = (252, 200, 55) if boss else (38, 32, 48)
    if boss:                                           # horns
        for sd in (-1, 1):
            pygame.draw.polygon(surf, (250, 245, 230), [(x + sd * .42 * r, y - .72 * r),
                                (x + sd * .95 * r, y - 1.42 * r), (x + sd * .86 * r, y - .5 * r)])
            pygame.draw.polygon(surf, edge, [(x + sd * .42 * r, y - .72 * r),
                                (x + sd * .95 * r, y - 1.42 * r), (x + sd * .86 * r, y - .5 * r)], 3)
    pygame.draw.circle(surf, hood, (int(x), int(y)), int(r))
    pygame.draw.circle(surf, edge, (int(x), int(y)), int(r), 3)
    if face:
        pygame.draw.polygon(surf, (245, 205, 160), ellipse_pts(x, y - .02 * r, .8 * r, .32 * r))
        brow = max(3, int((.1 if boss else .07) * r))
        for s_ in (-1, 1):
            pygame.draw.polygon(surf, (255, 255, 255), ellipse_pts(x + s_ * .32 * r, y - .02 * r, .17 * r, .13 * r))
            pygame.draw.circle(surf, (20, 20, 30), (int(x + s_ * .32 * r), int(y - .01 * r)), max(2, int(.075 * r)))
            pygame.draw.line(surf, (20, 20, 30), (x + s_ * .52 * r, y - .22 * r), (x + s_ * .1 * r, y - .12 * r), brow)
    pygame.draw.polygon(surf, band, [(x - .785 * r, y - .62 * r), (x + .785 * r, y - .62 * r),
                                     (x + .908 * r, y - .42 * r), (x - .908 * r, y - .42 * r)])
    fl = math.sin(t * 9) * .12 * r
    pygame.draw.polygon(surf, band, [(x + .85 * r, y - .55 * r), (x + 1.5 * r, y - .8 * r + fl), (x + 1.25 * r, y - .45 * r)])
    pygame.draw.polygon(surf, band, [(x + .85 * r, y - .5 * r), (x + 1.45 * r, y - .3 * r - fl), (x + 1.2 * r, y - .55 * r)])
    if face:
        pygame.draw.arc(surf, (140, 60, 50), (x - .22 * r, y + .12 * r, .44 * r, .3 * r), math.pi * 1.1, math.pi * 1.9, 3)
    if boss and fangs and face:                        # fangs
        for sd in (-1, 1):
            pygame.draw.polygon(surf, (255, 255, 255), [(x + sd * .12 * r, y + .2 * r),
                                (x + sd * .24 * r, y + .2 * r), (x + sd * .18 * r, y + .4 * r)])
    if flash > 0:                                      # white flash when hit
        circle_alpha(surf, (255, 255, 255, int(200 * min(1.0, flash))), (x, y), r)


def ninja_sprite(r, style="red", frame=0):
    """Polished enemy sprite; `frame` (0-5) animates the fluttering headband tails."""
    r = max(6, int(r))
    t = frame / 6 * (2 * math.pi / 9)
    return gfx.cached(("ninja", r, style, frame), lambda: gfx.icon_sprite(
        lambda s, c, rr: draw_ninja(s, c, rr, t, style, face=style != "boss"), r, pad=1.75, depth=0.25))


INK = (30, 22, 40)
SKIN, SKIN_DARK = (246, 206, 162), (215, 160, 120)
BRUISE, BRUISE_DARK = (125, 95, 190), (85, 55, 140)
BLOOD = (215, 30, 40)


def _boss_face(surf, c, r, stage, ouch=False):
    """The boss's face, worse after every hit (like the hero portrait in early Doom):
    0 angry, 1 swollen cheek + gap in the teeth, 2 black eye + bloody nose, 3 worried, plaster,
    open mouth, 4 dizzy spiral eyes, tongue out. ouch: eyes squeezed shut right after a hit."""
    x, y = c
    w = max(2, int(r * .045))
    pygame.draw.polygon(surf, SKIN, ellipse_pts(x, y + .08 * r, .74 * r, .5 * r, 0, 40))     # face opening
    if stage >= 1:                                    # swollen red cheek (left)
        pygame.draw.polygon(surf, (240, 120, 120), ellipse_pts(x - .48 * r, y + .2 * r, .2 * r, .16 * r, .2, 24))
        pygame.draw.polygon(surf, (250, 160, 150), ellipse_pts(x - .52 * r, y + .16 * r, .08 * r, .05 * r, .2, 14))
    # eyes
    for sd in (-1, 1):
        ex, ey = x + sd * .3 * r, y - .1 * r
        black = stage >= 2 and sd == 1 or stage >= 3
        if black:                                     # black eye: swollen purple ring
            pygame.draw.polygon(surf, BRUISE, ellipse_pts(ex, ey + .02 * r, .25 * r, .21 * r, 0, 28))
            pygame.draw.polygon(surf, BRUISE_DARK, ellipse_pts(ex, ey + .02 * r, .25 * r, .21 * r, 0, 28), w)
        if ouch:                                      # > <
            pygame.draw.lines(surf, INK, False, [(ex - sd * .12 * r, ey - .08 * r), (ex + sd * .08 * r, ey),
                                                 (ex - sd * .12 * r, ey + .08 * r)], w + 2)
        elif stage >= 4:                              # dizzy spirals
            pts = [(ex + math.cos(a) * r * .015 * a, ey + math.sin(a) * r * .015 * a) for a in [i * .4 for i in range(24)]]
            pygame.draw.polygon(surf, (255, 255, 255), ellipse_pts(ex, ey, .15 * r, .13 * r, 0, 20))
            pygame.draw.lines(surf, INK, False, pts, w)
        elif (stage >= 2 and sd == 1) or (stage == 1 and sd == -1):   # swollen shut / squinting
            pygame.draw.polygon(surf, (255, 255, 255), ellipse_pts(ex, ey + .03 * r, .14 * r, .05 * r, 0, 16))
            pygame.draw.circle(surf, INK, (int(ex), int(ey + .03 * r)), max(2, int(.04 * r)))
            pygame.draw.line(surf, INK, (ex - .16 * r, ey - .01 * r), (ex + .16 * r, ey - .01 * r), w)
        else:
            pygame.draw.polygon(surf, (255, 255, 255), ellipse_pts(ex, ey, .15 * r, .13 * r, 0, 20))
            pr = .06 * r if stage < 3 else .04 * r    # frightened: tiny pupils
            pygame.draw.circle(surf, INK, (int(ex - sd * .02 * r), int(ey + .01 * r)), max(2, int(pr)))
            pygame.draw.circle(surf, (255, 255, 255), (int(ex - sd * .02 * r - pr * .4), int(ey - pr * .3)),
                               max(1, int(pr * .35)))
        # brows: angry -> worried
        inner_up = stage >= 3
        bx0, by0 = ex - sd * .2 * r, ey - (.18 if not inner_up else .26) * r     # inner end
        bx1, by1 = ex + sd * .18 * r, ey - (.26 if not inner_up else .17) * r    # outer end
        if stage < 2:
            by0 += .06 * r
        pygame.draw.line(surf, INK, (bx0, by0), (bx1, by1), max(3, int(.08 * r)))
    if stage >= 3:                                    # a tear
        pygame.draw.polygon(surf, (120, 190, 255), ellipse_pts(x - .42 * r, y + .08 * r, .04 * r, .07 * r, 0, 12))
    # nose, bleeding from stage 2
    nose = pygame.Rect(0, 0, .2 * r, .15 * r)
    nose.center = (int(x), int(y + .1 * r))
    pygame.draw.ellipse(surf, SKIN_DARK if stage < 3 else (230, 120, 110), nose)
    for sd in (-1, 1):
        pygame.draw.circle(surf, (150, 90, 70), (int(x + sd * .04 * r), int(y + .14 * r)), max(1, int(.022 * r)))
    if stage >= 2:
        ln = (.16 if stage == 2 else .22) * r
        for sd in (-1, 1) if stage >= 3 else (1,):
            nx = x + sd * .045 * r
            pygame.draw.line(surf, BLOOD, (nx, y + .15 * r), (nx, y + .15 * r + ln), max(4, int(.05 * r)))
            pygame.draw.circle(surf, BLOOD, (int(nx), int(y + .15 * r + ln)), max(3, int(.045 * r)))
    # mouth with teeth that go missing
    my = y + .33 * r
    if stage <= 2:
        mouth = pygame.Rect(0, 0, .48 * r, (.13 + .04 * stage) * r)
        mouth.center = (int(x), int(my))
        pygame.draw.rect(surf, (90, 20, 35), mouth, border_radius=int(.05 * r))
        gaps = {0: (), 1: (2,), 2: (1, 4)}[stage]
        tw = mouth.w / 6
        for i in range(6):
            if i not in gaps:
                pygame.draw.rect(surf, (255, 255, 255), (mouth.x + i * tw + 1, mouth.y + 1, tw - 2, mouth.h * .45))
        for sd, keep in ((-1, stage == 0), (1, stage <= 1)):           # fangs
            if keep:
                fx = x + sd * .17 * r
                pygame.draw.polygon(surf, (255, 255, 255), [(fx - .05 * r, mouth.bottom - 2), (fx + .05 * r, mouth.bottom - 2),
                                                            (fx, mouth.bottom + .1 * r)])
        pygame.draw.rect(surf, INK, mouth, max(2, w - 1), border_radius=int(.05 * r))
    else:                                             # "ow!": round open mouth, then tongue out
        mouth = pygame.Rect(0, 0, .3 * r, .22 * r)
        mouth.center = (int(x + (.04 * r if stage >= 4 else 0)), int(my))
        pygame.draw.ellipse(surf, (90, 20, 35), mouth)
        pygame.draw.rect(surf, (255, 255, 255), (mouth.x + mouth.w * .55, mouth.y + 2, mouth.w * .18, mouth.h * .3))
        if stage >= 4:
            pygame.draw.polygon(surf, (240, 110, 130), ellipse_pts(mouth.centerx + .03 * r, mouth.bottom + .03 * r,
                                                                   .08 * r, .1 * r, 0, 16))
        pygame.draw.ellipse(surf, INK, mouth, max(2, w - 1))
    if stage >= 2:                                    # sweat drop at the temple
        pygame.draw.polygon(surf, (150, 210, 255), [(x + .62 * r, y - .2 * r), (x + .56 * r, y - .06 * r),
                                                    (x + .68 * r, y - .06 * r)])
        pygame.draw.circle(surf, (150, 210, 255), (int(x + .62 * r), int(y - .06 * r)), int(.06 * r))
    if stage >= 3:                                    # crossed plaster on the right cheek
        for a in (.7, -.7):
            ca, sa = math.cos(a), math.sin(a)
            px, py = x + .45 * r, y + .2 * r
            pts = [(px + ca * dx - sa * dy, py + sa * dx + ca * dy)
                   for dx, dy in ((-.15 * r, -.045 * r), (.15 * r, -.045 * r), (.15 * r, .045 * r), (-.15 * r, .045 * r))]
            pygame.draw.polygon(surf, (250, 220, 180), pts)
            pygame.draw.polygon(surf, (200, 150, 110), pts, max(1, w - 2))


def boss_stage(tg):
    """0 (fresh) .. 4 (nearly knocked out), spread over however many hits this boss can take."""
    dmg = tg.max_hp - tg.hp
    return min(4, round(dmg * 4 / max(1, tg.max_hp - 1)))


def boss_face_sprite(r, stage, ouch=False):
    r = max(6, int(r))
    return gfx.cached(("bossface", r, stage, ouch), lambda: gfx.icon_sprite(
        lambda s, c, rr: _boss_face(s, c, rr, stage, ouch), r, pad=1.75, depth=0.1, outline=3, shadow=0))


def heart_sprite(r, full=True):
    r = max(4, int(r))
    col = (240, 60, 85) if full else (255, 255, 255)

    def build():
        spr = gfx.icon_sprite(lambda s, c, rr: pygame.draw.polygon(s, col, heart_pts(c, rr)), r,
                              pad=1.2, puffy=full, outline=3, shadow=60)
        if not full:
            spr.set_alpha(130)
        return spr
    return gfx.cached(("heart", r, full), build)


def pow_sprite():
    def build():
        spr = gfx.icon_sprite(lambda s, c, r: pygame.draw.polygon(s, (255, 226, 60), star_pts(c, r, 0, .55, 10)),
                              110, pad=1.15, outline=6, depth=0.12)
        lab = gfx.label("POW!", 58, (235, 50, 40), outline=(255, 255, 255), width=5, shadow=False)
        spr.blit(lab, lab.get_rect(center=(spr.get_width() // 2, spr.get_height() // 2 - 4)))
        return spr
    return gfx.cached(("pow",), build)


def warning_sprite():
    """Boss alarm without words: a big red/yellow warning sign with "!"."""
    def draw(s, c, r):
        x, y = c
        pts = [(x, y - r), (x + r * 1.05, y + r * .8), (x - r * 1.05, y + r * .8)]
        pygame.draw.polygon(s, (255, 70, 60), pts)
        inner = [(x, y - r * .62), (x + r * .72, y + r * .58), (x - r * .72, y + r * .58)]
        pygame.draw.polygon(s, (255, 214, 60), inner)
        pygame.draw.rect(s, (44, 34, 72), (x - r * .09, y - r * .3, r * .18, r * .52), border_radius=int(r * .08))
        pygame.draw.circle(s, (44, 34, 72), (int(x), int(y + r * .4)), int(r * .1))
    return gfx.cached(("warning",), lambda: gfx.icon_sprite(draw, 120, pad=1.2, outline=6, depth=0.18))


def combo_sprite(n):
    def build():
        spr = gfx.icon_sprite(lambda s, c, r: pygame.draw.polygon(s, (255, 140, 40), star_pts(c, r, 0.2, .72, 12)),
                              64, pad=1.15, outline=5, depth=0.2)
        lab = gfx.label("x%d" % n, 52, (255, 255, 255))
        spr.blit(lab, lab.get_rect(center=(spr.get_width() // 2, spr.get_height() // 2)))
        return spr
    return gfx.cached(("combo", n), build)


def belt_sprite(col, w=120):
    return gfx.cached(("belt", tuple(col), w), lambda: gfx.icon_sprite(
        lambda s, c, r: draw_belt(s, (c[0], c[1] - r * .25), r * 2, col), w // 2, pad=1.0, depth=0.1))


# ---------------------------------------------------------------- Der blaue Ninja ---

HB_W = 240          # reference head width the headband sprite is built for


def headband_sprite():
    """Forehead band with a shiny metal plate (built once, then rotated/scaled per frame)."""
    def draw(s, c, r):
        k = r / (HB_W / 2)                         # px per reference px (supersampled)
        x, y = c
        top, bot = [], []
        for i in range(25):                        # curved like a band around a round head
            u = -1 + 2 * i / 24
            px = x + u * 0.62 * HB_W * k
            sag = 0.05 * HB_W * k * u * u
            top.append((px, y - 0.12 * HB_W * k + sag))           # a tall band (thick cloth)
            bot.append((px, y + 0.12 * HB_W * k + sag))
        pygame.draw.polygon(s, BLUE, top + bot[::-1])
        pygame.draw.lines(s, gfx.lighter(BLUE, 0.4), False, top[2:-2], max(2, int(6 * k)))
        pw, ph = 0.38 * HB_W * k, 0.22 * HB_W * k
        plate = pygame.Rect(0, 0, pw, ph)
        plate.center = (int(x), int(y))
        pygame.draw.rect(s, (200, 210, 228), plate, border_radius=int(ph * .3))
        pygame.draw.rect(s, (120, 130, 155), plate, max(2, int(4 * k)), border_radius=int(ph * .3))
        for dx in (-1, 1):                          # rivets
            pygame.draw.circle(s, (120, 130, 155), (int(x + dx * pw * .38), int(y)), int(ph * .09))
        pygame.draw.polygon(s, (60, 110, 220), star_pts((x, y), ph * .36, 0, .45))   # emblem
    return gfx.cached(("headband",), lambda: gfx.icon_sprite(draw, HB_W // 2, pad=1.35, outline=4,
                                                              depth=0.06, shadow=70))


def wrap_sprite(hw):
    """Cloth wrap around the wrist (forearm along x): rounded, with two bands of tape."""
    hw = max(6, int(hw))

    def draw(s, c, r):
        x, y = c
        body = pygame.Rect(0, 0, r * 1.6, r * 2)
        body.center = (int(x), int(y))
        pygame.draw.rect(s, BLUE, body, border_radius=int(r * .45))
        for dx in (-.35, .35):
            pygame.draw.line(s, gfx.lighter(BLUE, .5), (x + dx * r, y - r * .95), (x + dx * r, y + r * .95),
                             max(2, int(r * .18)))
    return gfx.cached(("wrap", hw), lambda: gfx.icon_sprite(draw, hw, pad=1.1, outline=3, depth=0.3, shadow=60))


class Ribbon:
    """A cloth tail hanging from a knot: a few points with verlet physics, so it trails
    behind when the head moves and flutters in a little wind."""
    N = 7

    def __init__(self, phase):
        self.p = None
        self.phase = phase

    def update(self, anchor, seg, t, dt):
        ax, ay = anchor
        if self.p is None or dt > 0.25 or abs(self.p[0][0] - ax) > 40 * seg:
            self.p = [[ax + i * seg, ay + i * seg * .3, ax + i * seg, ay + i * seg * .3] for i in range(self.N)]
        dt = min(dt, 1 / 30)
        wind = 22 * seg * (0.8 + 0.5 * math.sin(t * 6 + self.phase))      # px/s^2, blows to the right
        grav = 30 * seg
        damp = 0.04 ** dt                                                   # same feel at any frame rate
        for i, q in enumerate(self.p[1:], 1):       # verlet: x, y, previous x, previous y
            vx, vy = (q[0] - q[2]) * damp, (q[1] - q[3]) * damp
            q[2], q[3] = q[0], q[1]
            flutter = math.sin(t * 13 + self.phase + i * 0.9) * 40 * seg * i / self.N
            q[0] += vx + wind * dt * dt
            q[1] += vy + (grav + flutter) * dt * dt
        self.p[0][:] = [ax, ay, ax, ay]
        for _ in range(6):                          # keep the segment lengths
            for a, b in zip(self.p, self.p[1:]):
                dx, dy = b[0] - a[0], b[1] - a[1]
                d = math.hypot(dx, dy) or 1e-6
                f = (d - seg) / d
                if a is self.p[0]:
                    b[0] -= dx * f
                    b[1] -= dy * f
                else:
                    a[0] += dx * f * .5
                    a[1] += dy * f * .5
                    b[0] -= dx * f * .5
                    b[1] -= dy * f * .5

    def draw(self, surf, w0, w1):
        pts = [(q[0], q[1]) for q in self.p]
        left, right = [], []
        for i, (x, y) in enumerate(pts):
            a = pts[max(0, i - 1)]
            b = pts[min(len(pts) - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy) or 1.0
            w = w0 + (w1 - w0) * i / (len(pts) - 1)
            left.append((x - dy / d * w, y + dx / d * w))
            right.append((x + dy / d * w, y - dx / d * w))
        poly = left + right[::-1]
        pygame.draw.polygon(surf, BLUE_DARK, poly)
        pygame.draw.lines(surf, BLUE, False, left[:-1], max(2, int(w0 * .5)))
        pygame.draw.aalines(surf, gfx.INK, True, poly)


class PlayerNinja:
    """The blue ninja costume for one person: headband, flying tails, wrist wraps."""

    def __init__(self):
        self.tails = (Ribbon(0.0), Ribbon(1.9))
        self.last_t = None

    def draw(self, surf, pose, t):
        dt = 0.0 if self.last_t is None else t - self.last_t
        self.last_t = t
        if not pose.ok:
            return
        for s in "lr":                                       # wrist wraps
            if pose.has(f"{s}_wr", f"{s}_el", thr=0.4):
                wr, el = pose.P(f"{s}_wr"), pose.P(f"{s}_el")
                d = wr - el
                n = float(math.hypot(*d)) or 1.0
                ux, uy = d[0] / n, d[1] / n
                half_w = max(8.0, 0.12 * pose.shoulder_w())
                half_l = half_w * 0.8
                cx, cy = wr[0] - ux * half_l * 1.5, wr[1] - uy * half_l * 1.5
                wrap = wrap_sprite(int(half_w))
                gfx.blit_center(surf, wrap, (cx, cy), angle=-math.degrees(math.atan2(uy, ux)))
        head = pose.head()
        if not head:
            return
        eye_mid, hs, tilt = head
        # the ear landmarks wander when the head is turned or tilted: a head is about
        # 1.9 - 3.1 eye distances wide, so keep the costume inside that range
        eye_d = float(math.hypot(*(pose.P("l_eye") - pose.P("r_eye"))))
        if eye_d > 4:
            hs = min(max(hs, 1.9 * eye_d), 3.1 * eye_d)
        xf = Xf(eye_mid[0], eye_mid[1], hs, tilt)
        # band position on the head (head widths): up at the hairline, as wide as the head
        band_y, band_w = -.46, 1.0
        knot = xf.pt(.62 * band_w, band_y + .03)
        for i, tail in enumerate(self.tails):
            tail.update(knot, hs * (.11 if i == 0 else .09), t, dt)
            tail.draw(surf, hs * .075, hs * .045)
        band = headband_sprite()
        gfx.blit_center(surf, band, xf.pt(0, band_y), scale=band_w * hs / HB_W, angle=-math.degrees(tilt))
        gfx.blit_center(surf, gfx.ball(max(3, hs * .06), BLUE_DARK), knot)


def draw_belt(surf, c, w, col, t=0.0):
    x, y = c
    dark = tuple(int(v * 0.6) for v in col)
    edge = (210, 210, 220) if sum(col) < 220 else dark
    ow = max(2, int(w * 0.012))
    bh = .13 * w
    for s in (-1, 1):
        pts = [(x - s * .02 * w, y), (x + s * .04 * w, y), (x + s * .19 * w, y + .30 * w), (x + s * .07 * w, y + .35 * w)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, edge, pts, ow)
    band = pygame.Rect(x - w / 2, y - bh / 2, w, bh)
    pygame.draw.rect(surf, col, band, border_radius=int(bh * .3))
    pygame.draw.rect(surf, edge, band, ow, border_radius=int(bh * .3))
    knot = pygame.Rect(x - .08 * w, y - .11 * w, .16 * w, .22 * w)
    pygame.draw.rect(surf, col, knot, border_radius=int(.04 * w))
    pygame.draw.rect(surf, edge, knot, ow, border_radius=int(.04 * w))


class Target:
    def __init__(self, pos, kind, life, hp=1):
        self.x, self.y = pos
        self.kind, self.life, self.age = kind, life, 0.0     # kind: ninja | boss | board
        self.hp = self.max_hp = hp                           # the boss needs several hits
        self.flash = self.shake = 0.0                        # hit feedback timers
        self.last_hit = -9.0
        self.hit = False
        self.hit_t = 0.0
        self.vx = random.choice((-1, 1)) * random.uniform(200, 380)

    def scale(self):
        if self.hit:
            return max(0.0, 1.0 - self.hit_t / 0.7)
        if self.age < 0.35:
            return ease_out_back(self.age / 0.35)
        rest = self.life - self.age
        return 1.0 if rest > 0.3 else max(0.0, rest / 0.3)

    def pos(self):
        if self.hit:
            return (self.x + self.vx * self.hit_t, self.y - 380 * self.hit_t + 900 * self.hit_t ** 2 * .5)
        if self.shake > 0:
            k = min(1.0, self.shake * 4) * 9
            return (self.x + random.uniform(-k, k), self.y + random.uniform(-k, k))
        return (self.x, self.y)


class KungFuGame(Game):
    title = "Kung-Fu-Meister"
    speech = "Kung Fu! Hau die Ninjas mit Händen und Füßen!"
    DURATION = 45.0

    theme = (235, 95, 85)

    @staticmethod
    def icon(surf, c, r):
        draw_ninja(surf, c, r * .85, 0)

    def on_restart(self):
        self.targets, self.pows = [], []
        self.score, self.timer, self.spawn_t = 0, 0.0, 0.5
        self.combo, self.last_hit = 0, -9.0
        self.hist = {}
        self.belt = 0
        self.belt_t = -9.0
        self.kills_since_boss = 0
        self.boss_banner = 0.0
        self.hand_speed = {}
        self.fire, self._fire_acc = [], {}
        self.costumes = getattr(self, "costumes", {})      # slot -> PlayerNinja (keeps its tails)

    # ---- Geschwindigkeit der Hand über ~0.12 s ----
    def _speeds(self, named):
        out = {}
        for n, (x, y) in named.items():
            h = self.hist.setdefault(n, deque())
            h.append((self.t, x, y))
            while h and self.t - h[0][0] > 0.14:
                h.popleft()
            if len(h) >= 2:
                dt = h[-1][0] - h[0][0]
                out[n] = math.hypot(h[-1][1] - h[0][1], h[-1][2] - h[0][2]) / dt if dt > 0 else 0.0
            else:
                out[n] = 0.0
        for n in list(self.hist):
            if n not in named:
                del self.hist[n]
        return out

    def _free_spot(self, spots, minimum=210):
        random.shuffle(spots)
        for fx, fy in spots:
            p = (fx * self.W, fy * self.H)
            if all(math.hypot(p[0] - t.x, p[1] - t.y) > minimum for t in self.targets if not t.hit):
                return p
        return None

    def play_update(self, dt, pose, hands):
        lv = LEVELS[self.ctx.level]
        self.timer += dt
        named = dict(pose.named_hand_points()) if pose else {}
        speeds = self._speeds(named)
        self.hand_speed = {n: (named[n], speeds.get(n, 0.0)) for n in named}   # for the fire fists
        self._update_fire(dt, lv)
        self.spawn_t -= dt
        self.boss_banner = max(0.0, self.boss_banner - dt)
        active = [t for t in self.targets if not t.hit]
        boss_active = any(t.kind == "boss" and t.age < t.life for t in active)
        bs = BOSS[self.ctx.level]
        if (not boss_active and self.kills_since_boss >= bs["every"]
                and self.timer < self.DURATION - bs["life"] * 0.6):
            p = self._free_spot(list(HAND_SPOTS), minimum=300)
            if p:
                self.targets.append(Target(p, "boss", bs["life"], bs["hp"]))
                self.kills_since_boss = 0
                self.boss_banner = 1.8
                self.ctx.play("whoosh")
                self.ctx.play("gold")
                boss_active = True
        normal_active = len([t for t in active if t.kind != "boss"])
        if self.spawn_t <= 0 and normal_active < lv["n"] - (1 if boss_active else 0):
            p = self._free_spot(list(HAND_SPOTS))
            if p:
                self.targets.append(Target(p, "ninja", lv["life"]))
                self.ctx.play("whoosh")
            self.spawn_t = lv["every"] * random.uniform(0.7, 1.3)
        for tg in self.targets:
            tg.age += dt
            tg.flash = max(0.0, tg.flash - dt)
            tg.shake = max(0.0, tg.shake - dt)
            if tg.hit:
                tg.hit_t += dt
                continue
            if tg.age < 0.3:
                continue
            for n, (x, y) in named.items():
                reach = lv["r"] * (BOSS_SIZE if tg.kind == "boss" else 1) + 14
                need = lv["speed"]
                if tg.kind == "boss":
                    need = max(need, BOSS_MIN_SPEED)               # a resting arm never hurts a boss
                if math.hypot(x - tg.x, y - tg.y) < reach and speeds.get(n, 0) >= need:
                    if tg.kind == "boss":
                        if self.t - tg.last_hit >= BOSS_COOLDOWN:      # one swing counts once
                            self.hit_boss(tg)
                    else:
                        self.hit(tg)
                    break
            if not tg.hit and tg.age > tg.life:
                tg.age = 1e9
                self.ctx.play("down")
        self.targets = [t for t in self.targets if (t.age < t.life and not t.hit) or (t.hit and t.hit_t < 0.7)]
        self.pows = [(p[0], p[1], p[2] + dt, p[3]) for p in self.pows if p[2] < 0.45]
        if self.timer >= self.DURATION:
            self.finish(1 + (belt_index(self.score) * 4) // 6)

    def hit(self, tg):
        tg.hit = True
        self.score += 1
        self.combo = self.combo + 1 if self.t - self.last_hit < 1.6 else 1
        self.last_hit = self.t
        self.ctx.play("hit")
        self.pows.append((tg.x, tg.y, 0.0, random.uniform(-18, 18)))
        cols = [(255, 230, 80), (255, 140, 60), (255, 255, 255)]
        self.particles.burst((tg.x, tg.y), 8 + 2 * min(self.combo, 5), cols, 380, .6, (4, 9), 500, "star")
        if tg.kind == "ninja":
            self.kills_since_boss += 1
        self._check_belt()

    def _check_belt(self):
        b = belt_index(self.score)
        if b != self.belt:
            self.belt, self.belt_t = b, self.t
            self.ctx.play("cheer")
            self.ctx.say("Neuer Gürtel!")
            self.particles.confetti(self.W, 14)

    def hit_boss(self, tg):
        """A boss needs several hits: it shakes and flashes, only the last one knocks it out."""
        before = boss_stage(tg)
        tg.hp -= 1
        tg.last_hit, tg.flash, tg.shake = self.t, 0.25, 0.3
        self.score += 1
        self.combo = self.combo + 1 if self.t - self.last_hit < 1.6 else 1
        self.last_hit = self.t
        self.pows.append((tg.x, tg.y, 0.0, random.uniform(-18, 18)))
        cols = [(255, 230, 80), (255, 140, 60), (255, 255, 255)]
        r = LEVELS[self.ctx.level]["r"] * BOSS_SIZE
        now = boss_stage(tg)
        if before <= 2 and now > before:                    # teeth fly out (they are gone in the face)
            for i in range(min(2, now - before + 1)):
                self.particles.burst((tg.x + random.uniform(-.15, .15) * r, tg.y + .33 * r), 1, [(255, 255, 255)],
                                     260, 1.0, (6, 8), 900, "circle", up=320)
        if tg.hp > 0:
            self.ctx.play("board")
            self.particles.burst((tg.x, tg.y), 8, cols, 330, .5, (3, 8), 500, "star")
        else:
            tg.hit = True                                   # knocked out: flies away like the others
            self.score += BOSS_KILL_POINTS
            self.ctx.play("cheer")
            self.ctx.say("Boss besiegt!")
            self.particles.burst((tg.x, tg.y), 24, cols, 520, .9, (5, 12), 450, "star")
            self.particles.confetti(self.W, 25)
        self._check_belt()

    def play_draw(self, surf, pose):
        for p in (pose.all if pose else []):                 # everybody is a blue ninja
            self.costumes.setdefault(p.slot, PlayerNinja()).draw(surf, p, self.t)
        if self.boss_banner > 0:                             # red alarm glow at the screen edges
            v = gfx.vignette((self.W, self.H), (255, 30, 40), 220)
            v.set_alpha(int(255 * min(1.0, self.boss_banner / 0.6) * (0.6 + 0.4 * math.sin(self.t * 14))))
            surf.blit(v, (0, 0))
        frame = int(self.t * 9 / (2 * math.pi) * 6) % 6
        r0 = LEVELS[self.ctx.level]["r"]
        for tg in self.targets:
            sc = tg.scale()
            if sc <= 0.02:
                continue
            x, y = tg.pos()
            boss = tg.kind == "boss"
            r = r0 * (BOSS_SIZE if boss else 1)
            spr = ninja_sprite(r, "boss" if boss else "red", frame)
            stage = boss_stage(tg) if boss else 0
            ouch = boss and (self.t - tg.last_hit < 0.45 or tg.hit)
            dmg = boss_face_sprite(r, 4 if tg.hit else stage, ouch) if boss else None
            if tg.hit:                                       # knocked out: spins away
                ang = tg.hit_t * 720 * (1 if tg.vx > 0 else -1)
                gfx.blit_center(surf, spr, (x, y), scale=sc, angle=ang)
                if dmg:
                    gfx.blit_center(surf, dmg, (x, y), scale=sc, angle=ang)
                continue
            gfx.blit_center(surf, gfx.soft_shadow(1.5 * r, .32 * r), (tg.x, tg.y + .98 * r), scale=sc)
            squash = math.sin(tg.age * 22) * math.exp(-tg.age * 5) * 0.18      # wobble after popping up
            if boss and self.t - tg.last_hit < 0.5:                             # and after every hit
                squash += math.sin((self.t - tg.last_hit) * 30) * 0.15 * (1 - (self.t - tg.last_hit) / 0.5)
            bob = math.sin(self.t * 3 + tg.x * 0.01) * 4
            gfx.blit_center(surf, spr, (x, y + bob), scale=sc, sx=1 + squash, sy=1 - squash)
            if dmg:
                gfx.blit_center(surf, dmg, (x, y + bob), scale=sc, sx=1 + squash, sy=1 - squash)
            if tg.flash > 0:
                w = gfx.white_copy(spr)
                w.set_alpha(int(230 * min(1.0, tg.flash / 0.25)))
                gfx.blit_center(surf, w, (x, y + bob), scale=sc)
            n_stars = max(0, stage - 1) + (1 if boss and tg.hp == 1 else 0)
            for i in range(n_stars):                         # the more he got hit, the more stars circle
                if boss:
                    a = self.t * 4 + i * 2 * math.pi / n_stars
                    gfx.blit_center(surf, star_sprite(13, (255, 230, 80), 2),
                                    (x + math.cos(a) * r * .9, y - r * 1.05 + math.sin(a) * r * .25))
            if boss:                                         # hearts = hits left
                for i in range(tg.max_hp):
                    hx = tg.x + (i - (tg.max_hp - 1) / 2) * 40 * sc
                    gfx.blit_center(surf, heart_sprite(16, i < tg.hp), (hx, tg.y - r * 1.8), scale=sc)
        for x, y, t, ang in self.pows:
            k = ease_out_back(t / 0.18)
            fade = 1.0 if t < 0.3 else max(0.0, 1 - (t - 0.3) / 0.15)
            gfx.add_glow(surf, (x, y), 95 * k, (255, 200, 90), fade)
            gfx.blit_center(surf, pow_sprite(), (x, y), scale=max(0.05, k * (0.45 + 0.2 * fade) * fade), angle=ang)
        if self.state == "play":
            draw_timer(surf, (self.W / 2, self.H - 34), 360, 1 - self.timer / self.DURATION)
            gfx.blit_center(surf, belt_sprite(BELTS[self.belt][1]), (self.W - 110, 70),
                            scale=1 + 0.25 * max(0.0, 1 - (self.t - self.belt_t) / 0.5))
            if self.combo >= 3 and self.t - self.last_hit < 1.2:
                k = ease_out_back((self.t - self.last_hit) / 0.25)
                gfx.blit_center(surf, combo_sprite(min(self.combo, 30)), (self.W / 2, self.H * 0.72), scale=k)
            if self.boss_banner > 0:
                k = ease_out_back(min(1.0, (1.8 - self.boss_banner) / 0.35))
                out = max(0.0, 1 - self.boss_banner / 0.3)
                gfx.blit_center(surf, warning_sprite(), (self.W / 2 + random.uniform(-4, 4), self.H * 0.32),
                                scale=max(0.05, k * (1 - out)), angle=math.sin(self.t * 20) * 6)

    # ---- fire fists: hands always burn a little; a hit-fast hand blazes with a long trail ----
    def _update_fire(self, dt, lv):
        full = max(lv["speed"], 160)                        # speed for full fire (and for a hit)
        for p in self.fire:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] -= 260 * dt                                # flames rise
            p[4] -= dt
        self.fire = [p for p in self.fire if p[4] > 0]
        for n, ((x, y), v) in self._ball_points().items():   # one flame per hand, at the cursor ball
            k = min(1.0, 0.2 + 0.8 * v / full)
            self._fire_acc[n] = self._fire_acc.get(n, 0.0) + dt * (22 + 110 * k)
            while self._fire_acc[n] >= 1 and len(self.fire) < 500:
                self._fire_acc[n] -= 1
                life = random.uniform(0.18, 0.32) + 0.25 * k
                self.fire.append([x + random.uniform(-12, 12), y + random.uniform(-12, 12),
                                  random.uniform(-50, 50), random.uniform(-160, -40), life, life,
                                  (16 + 26 * k) * random.uniform(0.7, 1.2)])

    def _ball_points(self):
        """Per hand the point where the cursor ball is drawn: index finger, else wrist.
        {"r": ((x, y), speed), "l#1": ...}"""
        out = {}
        for n, val in self.hand_speed.items():
            base, _, who = n.partition("#")
            side, part = base.split("_")
            hand = side + ("#" + who if who else "")
            if part == "idx" or hand not in out:
                out[hand] = val
        return out

    def draw_hands(self, surf, pose):
        if self.state == "play":
            for x, y, _, _, life, maxl, size in self.fire:
                f = life / maxl                              # 1 = just born (hot) .. 0 = gone
                col, power = FIRE[0] if f > 0.7 else (FIRE[1] if f > 0.35 else FIRE[2])
                gfx.add_glow(surf, (x, y), int(size * (0.4 + 0.6 * f)) + 3, col, power)
            for n, ((x, y), v) in self._ball_points().items():   # hot core on fast hands
                if v >= max(LEVELS[self.ctx.level]["speed"], 160):
                    gfx.add_glow(surf, (x, y), 70, *FIRE_CORE[0])
                    gfx.add_glow(surf, (x, y), 30, *FIRE_CORE[1])
        draw_cursors(surf, pose, self.t)

    def result_draw(self, surf):
        b = belt_index(self.score)
        k = ease_out_back(self.state_t / 0.8)
        gfx.blit_center(surf, belt_sprite(BELTS[b][1], 380), (self.W // 2, self.H * 0.47), scale=max(0.05, k))

