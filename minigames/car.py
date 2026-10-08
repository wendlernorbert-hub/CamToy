"""Spiel 7: Auto fahren - beide Hände drehen ein Lenkrad, das Kind sitzt im Auto.

Die Linie von der linken zur rechten Hand ist das Lenkrad: Hände im Uhrzeigersinn drehen =
nach rechts lenken. Das Kind wird (per Personen-Maske) klein in den Fahrersitz eingeblendet,
das Lenkrad hängt an seinen Händen. Münzen einsammeln, Hütchen umfahren. Kein Verlieren:
ein Hütchen bremst nur kurz. Straße im Pseudo-3D-Stil (Scanlines), alles per Code gezeichnet.
"""
import math
import random

import numpy as np
import pygame

import gfx
from .common import Game, circle_alpha, draw_star, draw_stars_row, draw_timer, star_sprite, text

LEVELS = {1: dict(speed=34.0, curve=0.55, cones=0.22, lat=1.9, cent=0.35),
          2: dict(speed=46.0, curve=0.85, cones=0.42, lat=2.3, cent=0.60),
          3: dict(speed=60.0, curve=1.10, cones=0.60, lat=2.7, cent=0.90)}
DURATION = 50.0

D0 = 14.0                  # perspective: distance (world units) where a row's scale is 1/2
HORIZON = 0.30             # horizon height (fraction of screen)
DASH = 0.66                # dashboard top (fraction)
HALF_NEAR = 520.0          # half road width in px at scale 1
SEG = 6.0                  # length of one stripe segment (world units)
K_SHIFT = 1.0              # px of lateral road shift per row and unit of curvature
ANG_DEADZONE = 4.0         # degrees
ANG_FULL = 42.0            # degrees of wheel turn = full steering

# where the (scaled) player picture sits: (scale, left, top) as fractions of the screen
VIEW = (0.5, 0.25, 0.5)

GRASS = ((88, 172, 82), (76, 158, 72))
ROAD = ((96, 100, 114), (106, 110, 124))
RUMBLE = ((235, 70, 60), (245, 245, 245))


def curve_at(z):
    """Road curvature (about -1.2 .. 1.2) at world distance z; flat for the first stretch."""
    c = 0.72 * np.sin(z / 38.0 + 1.3) + 0.46 * np.sin(z / 17.0 + 0.4)
    return c * np.minimum(1.0, np.maximum(z, 0.0) / 90.0)


# ------------------------------------------------------------------ Wheel ---

_wheel_cache = {}


def wheel_sprite(size=320):
    if size not in _wheel_cache:
        k = 2
        z = size * k
        s = pygame.Surface((z, z), pygame.SRCALPHA)
        c = z // 2
        dark, mid, light = (34, 36, 46), (62, 66, 82), (120, 126, 150)
        ring = int(z * 0.085)
        for ang in (180, 0, 90):                         # spokes: left, right, down (T shape)
            a = math.radians(ang)
            ex, ey = c + math.cos(a) * z * 0.44, c + math.sin(a) * z * 0.44
            pygame.draw.line(s, dark, (c, c), (ex, ey), int(z * 0.1))
            pygame.draw.line(s, mid, (c, c), (ex, ey), int(z * 0.07))
        pygame.draw.circle(s, dark, (c, c), int(z * 0.5))
        pygame.draw.circle(s, (0, 0, 0, 0), (c, c), int(z * 0.5) - ring - 8)
        pygame.draw.circle(s, mid, (c, c), int(z * 0.5) - 5)
        pygame.draw.circle(s, (0, 0, 0, 0), (c, c), int(z * 0.5) - ring)
        pygame.draw.circle(s, light, (c, c), int(z * 0.5) - 5, 4)
        for ang in (180, 0, 90):                         # spokes drawn again over the hole
            a = math.radians(ang)
            ex, ey = c + math.cos(a) * (z * 0.5 - ring), c + math.sin(a) * (z * 0.5 - ring)
            pygame.draw.line(s, dark, (c, c), (ex, ey), int(z * 0.1))
            pygame.draw.line(s, mid, (c, c), (ex, ey), int(z * 0.07))
        pygame.draw.circle(s, dark, (c, c), int(z * 0.13))
        pygame.draw.circle(s, (230, 70, 60), (c, c), int(z * 0.1))
        pygame.draw.circle(s, (255, 150, 140), (int(c - z * .03), int(c - z * .03)), int(z * 0.03))
        # red marker at 12 o'clock so the turning is easy to see
        pygame.draw.rect(s, (255, 214, 60), (c - int(z * 0.03), int(z * 0.005), int(z * 0.06), ring + 6),
                         border_radius=int(z * 0.015))
        gfx.puff(s, z * 0.05)
        _wheel_cache[size] = gfx.sticker(pygame.transform.smoothscale(s, (size, size)), 4, shadow=90)
    return _wheel_cache[size]


def draw_wheel(surf, center, radius, angle_deg, alpha=255):
    spr = wheel_sprite()
    # pygame rotates counter-clockwise; rotozoom smooths the edges while turning
    img = pygame.transform.rotozoom(spr, -angle_deg, radius * 2 / 320)
    if alpha < 255:
        img.set_alpha(alpha)
    surf.blit(img, img.get_rect(center=(int(center[0]), int(center[1]))))


# --------------------------------------------------------------- Sprites ---

def draw_cone(surf, x, y, size):
    w, h = size * 0.5, size
    pts = [(x - w, y), (x + w, y), (x + w * 0.22, y - h), (x - w * 0.22, y - h)]
    pygame.draw.rect(surf, (230, 120, 40), (x - w * 1.2, y - h * 0.08, w * 2.4, h * 0.1),
                     border_radius=max(1, int(size * 0.04)))
    pygame.draw.polygon(surf, (250, 130, 40), pts)
    sw = [(x - w * 0.72, y - h * 0.38), (x + w * 0.72, y - h * 0.38),
          (x + w * 0.5, y - h * 0.58), (x - w * 0.5, y - h * 0.58)]
    pygame.draw.polygon(surf, (255, 255, 255), sw)
    pygame.draw.polygon(surf, (190, 80, 20), pts, max(1, int(size * 0.04)))


def draw_coin(surf, x, y, size, t):
    pulse = 1 + 0.08 * math.sin(t * 8 + x * 0.05)
    r = size * 0.62 * pulse
    if r < 3:
        return
    gfx.blit_center(surf, star_sprite(min(80, int(r))), (x, y - size * 0.5))


# -------------------------------------------------------------- Scenery ---
# Things beside the road, drawn once as polished sprites (ground at the bottom of the radius).

BR = 100                   # base radius of the scenery sprites in px
THEME_LEN = 230.0          # world units per landscape
THEMES = [                 # name, grass (2 stripes), what grows beside the road (weights)
    ("meadow", ((96, 182, 80), (84, 168, 70)), (("tree", 5), ("flowers", 3), ("sheep", 2))),
    ("forest", ((66, 150, 72), (56, 136, 64)), (("pine", 7), ("tree", 2), ("flowers", 1))),
    ("village", ((108, 186, 92), (96, 172, 82)), (("house", 6), ("tree", 2), ("flowers", 2))),
    ("beach", ((238, 214, 150), (228, 202, 138)), (("palm", 6), ("umbrella", 3), ("flowers", 1))),
]
SIZE = {"tree": 1.3, "pine": 1.5, "flowers": .45, "sheep": .55, "house": 1.35, "palm": 1.6, "umbrella": 1.0}


def theme_at(z):
    return THEMES[int(max(0.0, z) / THEME_LEN) % len(THEMES)]


def _scenery(surf, kind, c, r):
    x, y = c
    g = y + r                                                    # ground line
    if kind == "tree":
        pygame.draw.rect(surf, (130, 85, 50), (x - r * .12, g - r * .9, r * .24, r * .9), border_radius=int(r * .05))
        for dx, dy, k in ((0, -1.45, .55), (-.4, -1.05, .45), (.4, -1.05, .45), (0, -.95, .5)):
            pygame.draw.circle(surf, (70, 170, 75), (int(x + dx * r), int(g + dy * r)), int(k * r))
        for dx, dy in ((-.25, -1.5), (.3, -1.2), (-.45, -1.0), (.1, -.9)):
            pygame.draw.circle(surf, (235, 70, 70), (int(x + dx * r), int(g + dy * r)), int(.07 * r))
    elif kind == "pine":
        pygame.draw.rect(surf, (120, 80, 50), (x - r * .1, g - r * .4, r * .2, r * .4))
        for i, (w, top) in enumerate(((.62, 1.0), (.5, 1.45), (.36, 1.85))):
            pygame.draw.polygon(surf, (40, 130 + 15 * i, 70), [(x - w * r, g - (top - .55) * r), (x + w * r, g - (top - .55) * r),
                                                              (x, g - (top + .15) * r)])
    elif kind == "flowers":
        for dx in (-.8, -.3, .25, .75):
            pygame.draw.line(surf, (60, 140, 50), (x + dx * r, g), (x + dx * r, g - r * .7), max(2, int(r * .08)))
        for dx, col in ((-.8, (255, 90, 140)), (-.3, (255, 210, 60)), (.25, (160, 110, 255)), (.75, (255, 140, 60))):
            for k in range(5):
                a = k * 2 * math.pi / 5
                pygame.draw.circle(surf, col, (int(x + dx * r + math.cos(a) * r * .18), int(g - r * .75 + math.sin(a) * r * .18)),
                                   int(r * .14))
            pygame.draw.circle(surf, (255, 240, 150), (int(x + dx * r), int(g - r * .75)), int(r * .1))
    elif kind == "sheep":
        for dx in (-.45, -.15, .25, .5):
            pygame.draw.line(surf, (50, 45, 55), (x + dx * r, g - r * .4), (x + dx * r, g), max(3, int(r * .1)))
        for dx, dy in ((-.4, -.75), (0, -.85), (.4, -.75), (-.2, -.55), (.2, -.55)):
            pygame.draw.circle(surf, (250, 250, 250), (int(x + dx * r), int(g + dy * r)), int(r * .32))
        pygame.draw.ellipse(surf, (60, 55, 65), (x + r * .55, g - r * 1.1, r * .45, r * .38))
        pygame.draw.circle(surf, (255, 255, 255), (int(x + r * .82), int(g - r * .95)), max(2, int(r * .06)))
    elif kind == "house":
        col = (250, 225, 180)
        pygame.draw.rect(surf, col, (x - r * .7, g - r * .95, r * 1.4, r * .95))
        pygame.draw.polygon(surf, (220, 75, 65), [(x - r * .85, g - r * .9), (x, g - r * 1.6), (x + r * .85, g - r * .9)])
        pygame.draw.rect(surf, (140, 90, 60), (x - r * .15, g - r * .5, r * .3, r * .5), border_radius=int(r * .08))
        for dx in (-.45, .45):
            pygame.draw.rect(surf, (120, 190, 240), (x + dx * r - r * .14, g - r * .75, r * .28, r * .24))
        pygame.draw.rect(surf, (180, 80, 70), (x + r * .35, g - r * 1.5, r * .18, r * .35))
    elif kind == "palm":
        pts = [(x + math.sin(i / 8 * 1.2) * r * .35, g - i / 8 * r * 1.7) for i in range(9)]
        pygame.draw.lines(surf, (150, 105, 60), False, pts, max(4, int(r * .16)))
        tx, ty = pts[-1]
        for a in (-2.6, -2.0, -1.2, -.6, 0.0):
            ex, ey = tx + math.cos(a) * r * .8, ty + math.sin(a) * r * .5 + r * .25
            pygame.draw.polygon(surf, (60, 165, 70), [(tx, ty), (ex, ey), ((tx + ex) / 2, (ty + ey) / 2 + r * .14)])
        for dx in (-.08, .1):
            pygame.draw.circle(surf, (120, 80, 40), (int(tx + dx * r), int(ty + r * .1)), int(r * .09))
    elif kind == "umbrella":
        pygame.draw.line(surf, (240, 240, 240), (x, g), (x + r * .1, g - r * 1.1), max(3, int(r * .07)))
        for i in range(6):
            a0, a1 = math.pi + i * math.pi / 6, math.pi + (i + 1) * math.pi / 6
            col = (240, 70, 70) if i % 2 else (255, 255, 255)
            pygame.draw.polygon(surf, col, [(x + r * .1, g - r * 1.15),
                                            (x + r * .1 + math.cos(a0) * r * .75, g - r * 1.0 + math.sin(a0) * r * .3),
                                            (x + r * .1 + math.cos(a1) * r * .75, g - r * 1.0 + math.sin(a1) * r * .3)])


def scenery_sprite(kind):
    return gfx.cached(("scenery", kind), lambda: gfx.icon_sprite(lambda s, c, r: _scenery(s, kind, c, r), BR,
                                                                pad=2.0, outline=4, depth=0.15, shadow=50))


def rainbow_sprite():
    def draw(s, c, r):
        x, y = c
        cols = [(235, 60, 60), (255, 150, 40), (255, 225, 60), (90, 200, 90), (70, 150, 240), (150, 90, 220)]
        for i, col in enumerate(cols):
            pygame.draw.circle(s, col, (int(x), int(y + r * .55)), int(r * (1 - i * .08)))
        pygame.draw.circle(s, (0, 0, 0, 0), (int(x), int(y + r * .55)), int(r * .5))
        pygame.draw.rect(s, (0, 0, 0, 0), (0, y + r * .55, s.get_width(), s.get_height()))
        for sd in (-1, 1):                                       # clouds at both feet
            for dx, dy, k in ((0, 0, .16), (.14, .04, .12), (-.14, .05, .12)):
                pygame.draw.circle(s, (255, 255, 255), (int(x + sd * r * .78 + dx * r), int(y + r * .55 + dy * r)), int(k * r))
    return gfx.cached(("rainbow",), lambda: gfx.icon_sprite(draw, BR * 2, pad=1.1, outline=4, depth=0.1, shadow=0))


def cloud_sprite(k):
    def draw(s, c, r):
        for dx, dy, rr in ((0, 0, .5), (.45, .12, .38), (-.45, .14, .36), (.1, -.25, .38)):
            pygame.draw.circle(s, (255, 255, 255), (int(c[0] + dx * r), int(c[1] + dy * r)), int(rr * r))
    return gfx.cached(("cloud", k), lambda: gfx.icon_sprite(draw, 40 + 14 * k, pad=1.1, outline=0, depth=0.3, shadow=0))


def duck_sprite():
    """Rubber duck that sits on the dashboard and wobbles."""
    def draw(s, c, r):
        x, y = c
        pygame.draw.ellipse(s, (255, 214, 50), (x - r * .8, y - r * .05, r * 1.6, r * .9))
        pygame.draw.circle(s, (255, 214, 50), (int(x + r * .25), int(y - r * .3)), int(r * .45))
        pygame.draw.polygon(s, (255, 140, 30), [(x + r * .6, y - r * .35), (x + r * 1.0, y - r * .25), (x + r * .6, y - r * .12)])
        pygame.draw.circle(s, (30, 30, 40), (int(x + r * .38), int(y - r * .42)), max(2, int(r * .08)))
        pygame.draw.ellipse(s, (240, 180, 30), (x - r * .55, y + r * .1, r * .7, r * .35))
    return gfx.cached(("duck",), lambda: gfx.icon_sprite(draw, 40, pad=1.3, outline=3, depth=0.3))


def car_frame(W, H, yd):
    """The red car around the player: pillars, roof with mirror, hood, dashboard (made once)."""
    def build():
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        red, dark = (225, 55, 60), (170, 35, 45)
        pygame.draw.polygon(s, red, [(0, 0), (120, 0), (54, yd), (0, yd)])
        pygame.draw.polygon(s, red, [(W, 0), (W - 120, 0), (W - 54, yd), (W, yd)])
        pygame.draw.rect(s, red, (0, 0, W, 26))
        pygame.draw.rect(s, (40, 40, 55), (W // 2 - 92, 8, 184, 46), border_radius=18)
        pygame.draw.rect(s, (150, 195, 235), (W // 2 - 80, 15, 160, 32), border_radius=12)
        hood = [(W * .16, yd + 4), (W * .3, yd - 46), (W * .7, yd - 46), (W * .84, yd + 4)]
        pygame.draw.polygon(s, red, hood)
        pygame.draw.polygon(s, (255, 140, 140), [(W * .36, yd - 40), (W * .5, yd - 44), (W * .44, yd - 30)])
        dash = pygame.Rect(-20, yd - 4, W + 40, H - yd + 30)
        pygame.draw.rect(s, (70, 60, 90), dash, border_radius=40)
        pygame.draw.rect(s, (95, 85, 120), (20, yd + 6, W - 40, 22), border_radius=11)
        for cx in (W * .12, W * .905):                           # dial housings
            pygame.draw.circle(s, (55, 48, 72), (int(cx), yd + 112), 88)
        gfx.puff(s, 26)
        return gfx.sticker(s, 4, shadow=0)
    return gfx.cached(("carframe", W, H, yd), build)


class Obj:
    def __init__(self, kind, z, x):
        self.kind, self.z, self.x = kind, z, x
        self.prev_d = 1e9


# ------------------------------------------------------------------ Game ---

class CarGame(Game):
    title = "Auto fahren"
    needs_mask = True

    @staticmethod
    def icon(surf, c, r):
        draw_wheel(surf, c, r * 0.95, 14)

    # the main loop shows the player scaled into the driver's seat (see main.py)
    view = VIEW
    # the hands only reach inside that small picture: buttons sit where raised hands land
    home_at = (VIEW[1] + 0.1 * VIEW[0], VIEW[2] + 0.16 * VIEW[0])
    again_at = (VIEW[1] + 0.9 * VIEW[0], VIEW[2] + 0.16 * VIEW[0])

    def on_restart(self):
        W, H = self.W, self.H
        self.y_h = int(H * HORIZON)
        self.y_dash = int(H * DASH)
        self.hv = (self.y_dash - self.y_h) / 0.92         # scale 0.92 sits at the dashboard
        ys = np.arange(self.y_h + 1, self.y_dash)
        s = (ys - self.y_h) / self.hv
        self.rows = ys                                    # far -> near
        self.row_dist = D0 * (1.0 / s - 1.0)
        self.row_half = HALF_NEAR * s
        self.sky = self._make_sky()
        self.pos = 0.0
        self.x = 0.0
        self.speed = LEVELS[self.ctx.level]["speed"]
        self.bump_t = 0.0
        self.coins = 0
        self.timer = 0.0
        self.objs = []
        self.next_spawn = 55.0
        self.ang = 0.0                                    # smoothed wheel angle (deg, clockwise > 0)
        self.hand_mid = None                              # smoothed hand centre (px)
        self.wheel_r = 120.0
        self.have_hands = False
        self.driver = 0
        self.lost_t = 9.0
        self.shake = 0.0
        self.pulses = []                                  # (x, y, age) coin sparkles
        self.scenery = []                                 # (z, side, offset, kind) beside the road
        self.next_scene = {-1: 4.0, 1: 7.0}
        self.next_rainbow = 140.0
        self.duck_a = self.duck_v = 0.0                   # dashboard duck: wobble angle + speed
        self.ctx.tracker.set_segmentation(True)

    def on_exit(self):
        self.ctx.tracker.set_segmentation(False)

    # ---- scenery ----
    def _make_sky(self):
        W = self.W + 500
        h = self.y_h + 12
        s = pygame.Surface((W, h))
        for y in range(h):
            t = y / h
            pygame.draw.line(s, (int(90 + 130 * t), int(165 + 70 * t), int(235 + 15 * t)), (0, y), (W, y))
        sun = (int(W * 0.7), int(h * 0.42))
        gfx.add_glow(s, sun, 150, (255, 230, 150), 0.6)
        gfx.blit_center(s, gfx.ball(46, (255, 236, 150)), sun)
        rnd = random.Random(2)
        hills = pygame.Surface((W, h), pygame.SRCALPHA)
        for k, (col, amp, base) in enumerate((((130, 185, 160), 44, 0.80), ((100, 165, 120), 34, 0.9))):
            pts = [(0, h)]
            ph = rnd.uniform(0, 6)
            for x in range(0, W + 20, 20):
                pts.append((x, h * base - amp * (0.5 + 0.5 * math.sin(x / (110 + 40 * k) + ph))))
            pts.append((W, h))
            pygame.draw.polygon(hills, col, pts)
        s.blit(gfx.puff(hills, 18), (0, 0))
        return s

    # ---- input ----
    def _read_wheel(self, pose, dt):
        L = R = None
        # the driver is whoever holds the wheel with both hands; the last driver goes first
        for p in sorted(pose.all if pose else [], key=lambda p: p.slot != self.driver):
            for names in (("l_wr", "r_wr"), ("l_idx", "r_idx")):
                if p.has(*names, thr=0.35):
                    L, R = p.P(names[0]), p.P(names[1])
                    self.driver = p.slot
                    break
            if L is not None:
                break
        if L is not None:
            d = R - L
            if d[0] < 0:
                d = -d                                     # crossed hands: same line
            dist = float(np.hypot(d[0], d[1]))
            if dist > 60:
                ang = math.degrees(math.atan2(d[1], d[0]))
                ang = max(-80.0, min(80.0, ang))
                mid = (L + R) / 2
                k = min(1.0, dt * 14)
                self.ang += (ang - self.ang) * k
                if self.hand_mid is None:
                    self.hand_mid = (float(mid[0]), float(mid[1]))
                else:
                    self.hand_mid = (self.hand_mid[0] + (float(mid[0]) - self.hand_mid[0]) * k,
                                     self.hand_mid[1] + (float(mid[1]) - self.hand_mid[1]) * k)
                self.wheel_r += (max(85.0, min(190.0, dist * 0.56)) - self.wheel_r) * k
                self.have_hands, self.lost_t = True, 0.0
                return
        self.lost_t += dt
        if self.lost_t > 0.4:
            self.have_hands = False
            self.ang *= max(0.0, 1.0 - dt * 4)             # wheel eases back to straight

    def _steer(self):
        a = self.ang
        if abs(a) < ANG_DEADZONE:
            return 0.0
        a = a - math.copysign(ANG_DEADZONE, a)
        return max(-1.0, min(1.0, a / (ANG_FULL - ANG_DEADZONE)))

    # ---- logic ----
    def _spawn(self):
        lv = LEVELS[self.ctx.level]
        z = self.next_spawn
        if random.random() < lv["cones"]:
            xs = random.choice([-0.62, -0.22, 0.22, 0.62])
            self.objs.append(Obj("cone", z, xs))
            if random.random() < 0.4:                       # a second cone, always leaving a gap
                other = xs + random.choice([-0.9, 0.9])
                if abs(other) <= 0.9:
                    self.objs.append(Obj("cone", z, other))
        else:
            x0, drift = random.uniform(-0.65, 0.65), random.uniform(-0.07, 0.07)
            for i in range(4):
                self.objs.append(Obj("coin", z + i * 9.0, max(-0.85, min(0.85, x0 + drift * i))))
        self.next_spawn += random.uniform(48.0, 80.0)

    def play_update(self, dt, pose, hands):
        lv = LEVELS[self.ctx.level]
        self.timer += dt
        self.shake = max(0.0, self.shake - dt)
        self._read_wheel(pose, dt)
        steer = self._steer()

        offroad = abs(self.x) > 1.0
        self.bump_t = max(0.0, self.bump_t - dt)
        target = lv["speed"] * (0.55 if offroad else 1.0) * (0.4 if self.bump_t > 0 else 1.0)
        self.speed += (target - self.speed) * min(1.0, dt * 3)

        curve_now = float(curve_at(np.array([self.pos + 3.0]))[0]) * lv["curve"]
        self.x += steer * lv["lat"] * (self.speed / lv["speed"]) * dt
        self.x -= curve_now * lv["cent"] * (self.speed / lv["speed"]) * dt
        self.x = max(-1.35, min(1.35, self.x))
        self.pos += self.speed * dt

        while self.next_spawn < self.pos + 190:
            self._spawn()
        for side in (-1, 1):                              # trees, houses, ... beside the road
            while self.next_scene[side] < self.pos + 190:
                z = self.next_scene[side]
                kinds = theme_at(z)[2]
                kind = random.choices([k for k, _ in kinds], [w for _, w in kinds])[0]
                self.scenery.append((z, side, random.uniform(1.3, 2.2), kind))
                self.next_scene[side] += random.uniform(5.0, 10.0)
        if self.next_rainbow < self.pos + 190:
            self.scenery.append((self.next_rainbow, 0, 0.0, "rainbow"))
            self.next_rainbow += random.uniform(160.0, 230.0)
        self.scenery = [s for s in self.scenery if s[0] - self.pos > -2]
        # the duck wobbles with the steering and every bump (a spring)
        target = -steer * 22
        self.duck_v += (-(self.duck_a - target) * 60 - self.duck_v * 4) * dt
        self.duck_a += self.duck_v * dt
        for o in self.objs:
            d = o.z - self.pos
            if o.prev_d > 1.0 >= d and abs(o.x - self.x) < 0.24:
                self._touch(o)
            o.prev_d = d
        self.objs = [o for o in self.objs if o.z - self.pos > -4 and o.kind != "gone"]
        self.pulses = [(x, y, a + dt) for x, y, a in self.pulses if a + dt < 0.45]
        if self.timer >= DURATION:
            self.finish(1 + min(4, self.coins // 5))

    def _touch(self, o):
        px, py = self.W * 0.5, self.y_dash - 40
        if o.kind == "coin":
            self.coins += 1
            o.kind = "gone"
            self.ctx.play("good")
            self.pulses.append((px + (o.x - self.x) * 160, py, 0.0))
            self.particles.burst((px + (o.x - self.x) * 160, py), 10,
                                 [(255, 214, 40), (255, 255, 255)], 260, .5, (3, 7), 400, "star")
        else:
            o.kind = "gone"
            self.bump_t, self.shake = 1.4, 0.35
            self.duck_v += random.choice((-1, 1)) * 260
            self.ctx.play("boing")
            self.particles.burst((px + (o.x - self.x) * 160, py), 16,
                                 [(250, 130, 40), (255, 255, 255)], 300, .6, (3, 8), 500)

    # ---- drawing ----
    def _shifts(self):
        """Road centre offset (px) for every row, far -> near, from the curvature ahead."""
        lv = LEVELS[self.ctx.level]
        c = curve_at(self.pos + self.row_dist[::-1]) * lv["curve"]       # near -> far
        return (np.cumsum(c) * K_SHIFT)[::-1]

    def draw_back(self, surf, pose):
        W, H = self.W, self.H
        shift = self._shifts()
        ox = int((self.shake > 0) * random.uniform(-6, 6) * min(1.0, self.shake * 4))
        # sky with parallax: scenery slides against the curvature at the horizon
        sky_x = -250 + int(shift[0] * 0.45) + ox
        surf.blit(self.sky, (sky_x, 0))
        for i in range(6):                                  # clouds drift slowly
            cx = (i * 260 + self.t * (8 + 3 * i) + sky_x * 0.5) % (W + 300) - 150
            gfx.blit_center(surf, cloud_sprite(i % 3), (cx, 40 + (i * 37) % (self.y_h - 90)))
        rows, dist, half = self.rows, self.row_dist, self.row_half
        for i in range(len(rows)):
            y = int(rows[i])
            z = self.pos + dist[i]
            seg = int(z / SEG) & 1
            cx = W * 0.5 + shift[i] - self.x * half[i] + ox
            h = half[i]
            pygame.draw.line(surf, theme_at(z)[1][seg], (0, y), (W, y))
            rw = max(1.0, h * 0.075)
            pygame.draw.line(surf, RUMBLE[seg], (cx - h - rw, y), (cx + h + rw, y))
            pygame.draw.line(surf, ROAD[seg], (cx - h, y), (cx + h, y))
            if seg == 0:
                dw = max(1.0, h * 0.03)
                pygame.draw.line(surf, (255, 255, 255), (cx - dw, y), (cx + dw, y))
        # stars, cones and the scenery, far to near
        things = [(o.z, o) for o in self.objs] + [(s[0], s) for s in self.scenery]
        for z, o in sorted(things, key=lambda e: -e[0]):
            d = z - self.pos
            if d <= 0:
                continue
            sc = 1.0 / (1.0 + d / D0)
            y = self.y_h + sc * self.hv
            if y > self.y_dash + 30 or y < self.y_h + 2:
                continue
            idx = max(0, min(len(rows) - 1, int(y - rows[0])))
            if isinstance(o, tuple):                        # scenery: (z, side, offset, kind)
                _, side, off, kind = o
                x = W * 0.5 + shift[idx] + (side * off - self.x) * half[idx] + ox
                if kind == "rainbow":
                    k = half[idx] * 2.9 / (2 * BR * 2)
                    spr = rainbow_sprite()
                    if spr.get_width() * k > 6:
                        gfx.blit_center(surf, spr, (x, y - BR * 2 * k * .45), scale=k)
                    continue
                k = sc * SIZE[kind] * 0.9
                if BR * k < 3:
                    continue
                q = max(1, round(k * 40)) / 40                  # a few cached sizes, smooth enough
                spr = gfx.cached(("scn", kind, q), lambda kind=kind, q=q: pygame.transform.smoothscale_by(
                    scenery_sprite(kind), q), fleeting=True)
                surf.blit(spr, spr.get_rect(center=(int(x), int(y - BR * q))))
                continue
            x = W * 0.5 + shift[idx] + (o.x - self.x) * half[idx] + ox
            size = 118 * sc
            if o.kind == "cone":
                draw_cone(surf, x, y, size)
            elif o.kind == "coin":
                draw_coin(surf, x, y, size * 0.9, self.t)
        self._draw_dashboard(surf)

    def _draw_dashboard(self, surf):
        W, H, yd = self.W, self.H, self.y_dash
        gfx.blit_center(surf, car_frame(W, H, yd), (W / 2, H / 2))
        # speedometer (left) and star counter (right)
        lv = LEVELS[self.ctx.level]
        cy = yd + 112
        cx = W * 0.12
        gfx.blit_center(surf, gfx.ball(74, (245, 245, 252), rim=(255, 200, 60)), (cx, cy))
        for k in range(9):
            a = math.radians(150 + k * 30)
            col = (90, 200, 100) if k < 4 else ((255, 200, 60) if k < 7 else (240, 80, 70))
            pygame.draw.line(surf, col, (cx + math.cos(a) * 48, cy + math.sin(a) * 48),
                             (cx + math.cos(a) * 62, cy + math.sin(a) * 62), 6)
        a = math.radians(150 + 240 * min(1.0, self.speed / (lv["speed"] * 1.1)))
        pygame.draw.line(surf, (230, 50, 50), (cx, cy), (cx + math.cos(a) * 52, cy + math.sin(a) * 52), 7)
        gfx.blit_center(surf, gfx.ball(11, (70, 60, 90)), (cx, cy))
        sx = W * 0.905
        gfx.blit_center(surf, gfx.ball(74, (70, 60, 100), rim=(255, 200, 60)), (sx, cy))
        gfx.blit_center(surf, star_sprite(40), (sx, cy - 12), scale=1 + 0.06 * math.sin(self.t * 4))
        gfx.blit_center(surf, gfx.label(str(self.coins), 40, (255, 255, 255)), (sx, cy + 42))
        # the rubber duck on the dashboard
        gfx.blit_center(surf, duck_sprite(), (W * 0.8, yd - 22), angle=self.duck_a)

    def play_draw(self, surf, pose):
        W, H = self.W, self.H
        if self.state == "play":
            draw_timer(surf, (W / 2, H - 34), 360, 1 - self.timer / DURATION)
        for x, y, a in self.pulses:
            circle_alpha(surf, (255, 235, 120, max(0, min(255, int(200 * (1 - a / 0.45))))), (x, y), 20 + 60 * a, 4)
        if self.have_hands and self.hand_mid:
            draw_wheel(surf, self.hand_mid, self.wheel_r, self.ang)
        else:                                   # ghost wheel: "put both hands here"
            cx, cy = W * 0.5, H * 0.80
            draw_wheel(surf, (cx, cy), 120, self.ang, 110)
            p = 0.5 + 0.5 * math.sin(self.t * 5)
            for dx in (-120, 120):
                circle_alpha(surf, (255, 225, 60, int(90 + 120 * p)), (cx + dx, cy), 26 + 6 * p)
        if self.state == "play" and abs(self.x) > 1.0:        # off the road: arrows point back to it
            d = -1 if self.x > 0 else 1
            for i in range(3):
                k = (self.t * 2 + i / 3) % 1.0
                ax = W / 2 + d * (40 + 90 * k)
                pts = [(ax + d * 30, self.y_h + 40), (ax, self.y_h + 10), (ax, self.y_h + 70)]
                gfx.add_glow(surf, (ax + d * 10, self.y_h + 40), 40, (255, 210, 90), 0.6 * math.sin(k * math.pi))
                pygame.draw.polygon(surf, (255, 225, 80), pts)
                pygame.draw.aalines(surf, gfx.INK, True, pts)

    def result_draw(self, surf):
        draw_wheel(surf, (self.W // 2, self.H * 0.62), 80, math.sin(self.state_t * 3) * 25)
