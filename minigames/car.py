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

from .common import Game, circle_alpha, draw_star, draw_stars_row, text

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
        _wheel_cache[size] = pygame.transform.smoothscale(s, (size, size))
    return _wheel_cache[size]


def draw_wheel(surf, center, radius, angle_deg, alpha=255):
    img = pygame.transform.smoothscale(wheel_sprite(), (int(radius * 2), int(radius * 2)))
    img = pygame.transform.rotate(img, -angle_deg)        # pygame rotates counter-clockwise
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
    draw_star(surf, (x, y - size * 0.5), size * 0.62 * pulse, (255, 214, 40), t * 0.8,
              outline=(190, 120, 0))


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
        self.lost_t = 9.0
        self.shake = 0.0
        self.pulses = []                                  # (x, y, age) coin sparkles
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
        pygame.draw.circle(s, (255, 244, 190), (int(W * 0.7), int(h * 0.42)), 46)
        rnd = random.Random(2)
        for _ in range(7):                                  # clouds
            cx, cy = rnd.randint(0, W), rnd.randint(10, int(h * 0.55))
            for dx, dy, r in ((0, 0, 26), (28, 6, 20), (-26, 8, 18), (6, -12, 18)):
                pygame.draw.circle(s, (255, 255, 255), (cx + dx, cy + dy), r)
        for k, (col, amp, base) in enumerate((((120, 170, 150), 44, 0.80), ((92, 150, 112), 34, 0.9))):
            pts = [(0, h)]
            ph = rnd.uniform(0, 6)
            for x in range(0, W + 20, 20):
                pts.append((x, h * base - amp * (0.5 + 0.5 * math.sin(x / (110 + 40 * k) + ph))))
            pts.append((W, h))
            pygame.draw.polygon(s, col, pts)
        return s

    # ---- input ----
    def _read_wheel(self, pose, dt):
        L = R = None
        if pose:
            for names in (("l_wr", "r_wr"), ("l_idx", "r_idx")):
                if pose.has(*names, thr=0.35):
                    L, R = pose.P(names[0]), pose.P(names[1])
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
        surf.blit(self.sky, (-250 + int(shift[0] * 0.45) + ox, 0))
        rows, dist, half = self.rows, self.row_dist, self.row_half
        for i in range(len(rows)):
            y = int(rows[i])
            seg = int((self.pos + dist[i]) / SEG) & 1
            cx = W * 0.5 + shift[i] - self.x * half[i] + ox
            h = half[i]
            pygame.draw.line(surf, GRASS[seg], (0, y), (W, y))
            rw = max(1.0, h * 0.075)
            pygame.draw.line(surf, RUMBLE[seg], (cx - h - rw, y), (cx + h + rw, y))
            pygame.draw.line(surf, ROAD[seg], (cx - h, y), (cx + h, y))
            if seg == 0:
                dw = max(1.0, h * 0.03)
                pygame.draw.line(surf, (255, 255, 255), (cx - dw, y), (cx + dw, y))
        # objects, far to near
        for o in sorted(self.objs, key=lambda o: -o.z):
            d = o.z - self.pos
            if d <= 0:
                continue
            sc = 1.0 / (1.0 + d / D0)
            y = self.y_h + sc * self.hv
            if y > self.y_dash + 30 or y < self.y_h + 2:
                continue
            idx = max(0, min(len(rows) - 1, int(y - rows[0])))
            x = W * 0.5 + shift[idx] + (o.x - self.x) * half[idx] + ox
            size = 118 * sc
            if o.kind == "cone":
                draw_cone(surf, x, y, size)
            elif o.kind == "coin":
                draw_coin(surf, x, y, size * 0.9, self.t)
        self._draw_dashboard(surf)

    def _draw_dashboard(self, surf):
        W, H, yd = self.W, self.H, self.y_dash
        pygame.draw.polygon(surf, (36, 40, 56), [(0, 0), (110, 0), (46, yd), (0, yd)])
        pygame.draw.polygon(surf, (36, 40, 56), [(W, 0), (W - 110, 0), (W - 46, yd), (W, yd)])
        pygame.draw.rect(surf, (30, 33, 46), (W // 2 - 90, 0, 180, 44), border_bottom_left_radius=18,
                         border_bottom_right_radius=18)
        pygame.draw.rect(surf, (140, 175, 205), (W // 2 - 76, 6, 152, 26), border_radius=10)
        pygame.draw.rect(surf, (50, 54, 72), (0, yd, W, H - yd))
        pygame.draw.rect(surf, (96, 102, 128), (0, yd - 6, W, 12), border_radius=6)
        pygame.draw.rect(surf, (70, 76, 100), (0, yd + 6, W, 8))
        pygame.draw.ellipse(surf, (60, 66, 88), (W * 0.30, yd - 26, W * 0.40, 70))
        # speedometer (left) and coin counter (right)
        lv = LEVELS[self.ctx.level]
        for cx, kind in ((W * 0.14, "speed"), (W * 0.86, "coins")):
            cy = yd + 108
            pygame.draw.circle(surf, (24, 26, 36), (int(cx), cy), 84)
            pygame.draw.circle(surf, (120, 128, 156), (int(cx), cy), 84, 5)
            if kind == "speed":
                for k in range(9):
                    a = math.radians(150 + k * 30)
                    pygame.draw.line(surf, (200, 205, 225), (cx + math.cos(a) * 62, cy + math.sin(a) * 62),
                                     (cx + math.cos(a) * 74, cy + math.sin(a) * 74), 3)
                a = math.radians(150 + 240 * min(1.0, self.speed / (lv["speed"] * 1.1)))
                pygame.draw.line(surf, (255, 90, 70), (cx, cy), (cx + math.cos(a) * 58, cy + math.sin(a) * 58), 5)
                pygame.draw.circle(surf, (200, 205, 225), (int(cx), cy), 8)
            else:
                draw_star(surf, (cx, cy), 46 + 4 * math.sin(self.t * 4), (255, 214, 40), 0, outline=(190, 120, 0))

    def play_draw(self, surf, pose):
        W, H = self.W, self.H
        if self.state == "play":
            draw_stars_row(surf, (W / 2, 62), 10, min(10, self.coins // 2), 30)
            w = 340
            x0, y0 = W / 2 - w / 2, 102
            pygame.draw.rect(surf, (255, 255, 255), (x0 - 3, y0 - 3, w + 6, 18), border_radius=9)
            pygame.draw.rect(surf, (255, 170, 60), (x0, y0, w * max(0, 1 - self.timer / DURATION), 12),
                             border_radius=6)
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
        if self.state == "play" and abs(self.x) > 1.0:
            text(surf, "◄ ►", 40, (W / 2, self.y_h - 20), (255, 230, 120))

    def result_draw(self, surf):
        draw_wheel(surf, (self.W // 2, self.H * 0.62), 80, math.sin(self.state_t * 3) * 25)
