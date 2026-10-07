"""Spiel 6: Pizza belegen - Zutaten greifen, über die Pizza streuen, in den Ofen schieben.

Kein Verlieren: Wer fertig ist (Ofen-Knopf) oder nach 90 Sekunden, schiebt die Pizza in den Ofen
und bekommt Sterne nach Menge und Vielfalt der Zutaten.
"""
import math
import random

import pygame

from .common import (DwellButton, Game, circle_alpha, draw_ring, ease_out_back, ellipse_pts,
                     text)

R = 188                       # Pizza-Radius
MAX_TOPPINGS = 80
PICK_TIME = 0.5               # Hand so lange auf der Zutat halten
DROPS_PER_PICK = 4
DROP_GAP = 0.22               # Sekunden zwischen zwei gestreuten Zutaten
DROP_DIST = 46                # Hand muss sich zwischen zwei Zutaten so weit bewegen
HOLD_TIMEOUT = 10.0
MAX_TIME = 90.0
BAKE_TIME = 2.6

KINDS = ["salami", "mushroom", "pepper", "olive", "pineapple", "cheese"]
NAMES = {"salami": "Salami", "mushroom": "Pilze", "pepper": "Paprika",
         "olive": "Oliven", "pineapple": "Ananas", "cheese": "Käse"}
S = 72                        # Sprite-Größe in Pixeln


# ------------------------------------------------------------------ Zutaten ---

def make_topping(kind, size=S):
    """Zeichnet eine Zutat (Alpha-Surface size x size), zweifach überabgetastet."""
    k = 2
    z = size * k
    s = pygame.Surface((z, z), pygame.SRCALPHA)
    c = z // 2
    if kind == "salami":
        pygame.draw.circle(s, (120, 35, 35), (c, c), int(z * 0.47))
        pygame.draw.circle(s, (200, 70, 62), (c, c), int(z * 0.43))
        for dx, dy in ((-.18, -.12), (.14, -.2), (.2, .12), (-.08, .2), (0, 0)):
            pygame.draw.circle(s, (238, 140, 125), (int(c + dx * z), int(c + dy * z)), int(z * 0.05))
    elif kind == "mushroom":
        stem = pygame.Rect(0, 0, int(z * 0.26), int(z * 0.34))
        stem.midtop = (c, int(c + z * 0.02))
        pygame.draw.rect(s, (248, 238, 218), stem, border_radius=int(z * 0.07))
        pygame.draw.rect(s, (170, 135, 100), stem, max(2, k), border_radius=int(z * 0.07))
        cap = pygame.Rect(0, 0, int(z * 0.86), int(z * 0.6))
        cap.midbottom = (c, int(c + z * 0.1))
        pygame.draw.ellipse(s, (170, 135, 100), cap)
        pygame.draw.ellipse(s, (232, 205, 170), cap.inflate(-max(4, z // 18), -max(4, z // 18)))
        pygame.draw.ellipse(s, (246, 228, 200), (cap.x + z * .16, cap.y + z * .1, z * .24, z * .12))
    elif kind == "pepper":
        pygame.draw.circle(s, (45, 120, 40), (c, c), int(z * 0.46))
        pygame.draw.circle(s, (95, 190, 70), (c, c), int(z * 0.43))
        pygame.draw.circle(s, (0, 0, 0, 0), (c, c), int(z * 0.27))
        pygame.draw.circle(s, (45, 120, 40), (c, c), int(z * 0.27), max(2, k))
        pygame.draw.arc(s, (170, 235, 140), (c - z * .35, c - z * .35, z * .7, z * .7),
                        math.radians(110), math.radians(200), max(3, z // 18))
    elif kind == "olive":
        pygame.draw.circle(s, (20, 20, 28), (c, c), int(z * 0.34))
        pygame.draw.circle(s, (52, 54, 66), (c, c), int(z * 0.3))
        pygame.draw.circle(s, (0, 0, 0, 0), (c, c), int(z * 0.12))
        pygame.draw.circle(s, (20, 20, 28), (c, c), int(z * 0.12), max(2, k))
        pygame.draw.circle(s, (130, 135, 160), (int(c - z * .12), int(c - z * .14)), int(z * 0.05))
    elif kind == "pineapple":
        pts = [(c - z * .38, c + z * .3), (c - z * .28, c - z * .3), (c + z * .3, c - z * .22),
               (c + z * .4, c + z * .28)]
        pygame.draw.polygon(s, (190, 150, 30), pts)
        inner = [(c - z * .31, c + z * .24), (c - z * .23, c - z * .24), (c + z * .24, c - z * .17),
                 (c + z * .32, c + z * .22)]
        pygame.draw.polygon(s, (255, 226, 80), inner)
        for t in (-.12, .06, .22):
            pygame.draw.line(s, (235, 195, 50), (c - z * .25, c + z * t), (c + z * .3, c + z * (t - .05)),
                             max(2, k))
    else:   # cheese: ein paar gelbe Fäden
        for dx, dy, a in ((-.2, -.12, 20), (.12, -.18, -25), (-.05, .1, 60), (.2, .16, -50)):
            x0, y0 = c + dx * z, c + dy * z
            ln = z * .22
            ang = math.radians(a)
            p0 = (x0 - math.cos(ang) * ln, y0 - math.sin(ang) * ln)
            p1 = (x0 + math.cos(ang) * ln, y0 + math.sin(ang) * ln)
            pygame.draw.line(s, (205, 160, 40), p0, p1, max(5, z // 9))
            pygame.draw.line(s, (255, 226, 100), p0, p1, max(3, z // 14))
    return pygame.transform.smoothscale(s, (size, size))


_pizza_cache = {}


def pizza_base():
    """Brett, Teig, Soße (einmal gezeichnet)."""
    if "base" not in _pizza_cache:
        z = (R + 60) * 2
        s = pygame.Surface((z, z), pygame.SRCALPHA)
        c = z // 2
        pygame.draw.circle(s, (0, 0, 0, 60), (c + 6, c + 10), R + 40)
        pygame.draw.circle(s, (120, 78, 45), (c, c), R + 36)
        pygame.draw.circle(s, (160, 108, 62), (c, c), R + 30)
        pygame.draw.circle(s, (176, 120, 70), (c, c), R + 22, 3)
        pygame.draw.circle(s, (170, 118, 60), (c, c), R)
        pygame.draw.circle(s, (232, 182, 100), (c, c), R - 4)
        rnd = random.Random(4)
        for _ in range(26):                       # Teigblasen am Rand
            a = rnd.uniform(0, 2 * math.pi)
            rr = R - 14
            pygame.draw.circle(s, (246, 208, 132), (int(c + math.cos(a) * rr), int(c + math.sin(a) * rr)),
                               rnd.randint(4, 8))
        pygame.draw.circle(s, (170, 60, 40), (c, c), R - 28)
        pygame.draw.circle(s, (208, 66, 44), (c, c), R - 32)
        for _ in range(40):                       # Soßen-Glanz
            a, d = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, R - 46)
            pygame.draw.circle(s, (222, 90, 60), (int(c + math.cos(a) * d), int(c + math.sin(a) * d)),
                               rnd.randint(3, 7))
        _pizza_cache["base"] = s
    return _pizza_cache["base"]


def baked_overlay():
    """Goldbrauner Hauch für die gebackene Pizza."""
    if "baked" not in _pizza_cache:
        z = (R + 60) * 2
        s = pygame.Surface((z, z), pygame.SRCALPHA)
        c = z // 2
        for i in range(10):
            pygame.draw.circle(s, (210, 120, 30, 9), (c, c), R - 2 - i * 3, 0)
        pygame.draw.circle(s, (160, 90, 20, 70), (c, c), R, 14)
        _pizza_cache["baked"] = s
    return _pizza_cache["baked"]


def draw_pizza_icon(surf, c, r):
    pygame.draw.circle(surf, (232, 182, 100), c, r)
    pygame.draw.circle(surf, (208, 66, 44), c, int(r * 0.8))
    for dx, dy in ((-.3, -.25), (.32, -.1), (-.05, .35), (.1, -.42)):
        pygame.draw.circle(surf, (120, 35, 35), (int(c[0] + dx * r), int(c[1] + dy * r)), int(r * 0.2))
        pygame.draw.circle(surf, (200, 70, 62), (int(c[0] + dx * r), int(c[1] + dy * r)), int(r * 0.16))
    pygame.draw.circle(surf, (250, 226, 120), (int(c[0] + .38 * r), int(c[1] + .32 * r)), int(r * 0.1))


def icon_oven(surf, c, r):
    x, y = c
    body = pygame.Rect(0, 0, r * 1.7, r * 1.45)
    body.center = (x, y)
    pygame.draw.rect(surf, (80, 85, 105), body, border_radius=int(r * 0.2))
    win = body.inflate(-r * 0.6, -r * 0.7)
    win.y += int(r * 0.12)
    pygame.draw.rect(surf, (255, 150, 40), win, border_radius=int(r * 0.12))
    pygame.draw.rect(surf, (255, 215, 90), win.inflate(-r * 0.5, -r * 0.5), border_radius=int(r * 0.1))
    for dx in (-0.5, 0, 0.5):
        pygame.draw.circle(surf, (230, 230, 240), (int(x + dx * r), int(body.top + r * 0.18)), int(r * 0.08))


# --------------------------------------------------------------------- Spiel ---

class Bin:
    def __init__(self, kind, center):
        self.kind, self.c, self.r = kind, center, 54
        self.progress, self.hover, self.armed = 0.0, False, True
        self.sprite = make_topping(kind, 64)


class PizzaGame(Game):
    title = "Pizza belegen"

    @staticmethod
    def icon(surf, c, r):
        draw_pizza_icon(surf, c, int(r * 0.9))

    def on_restart(self):
        self.toppings = []             # (kind, x, y, sprite)
        self.held = None               # dict(kind, side, left, t)
        self.last_drop = (-9.0, None)  # (Zeit, Position)
        self.phase, self.phase_t, self.timer = "decorate", 0.0, 0.0
        self.center = (self.W * 0.5, self.H * 0.57)
        ys = (0.35, 0.56, 0.77)
        self.bins = [Bin(k, (self.W * (0.095 if i < 3 else 0.905), self.H * ys[i % 3]))
                     for i, k in enumerate(KINDS)]
        self.oven = DwellButton((self.W - 72, 76), 50, 1.2, icon_oven)
        self._sprites = {}

    # ---- Hilfen ----
    def _sprite(self, kind, angle):
        key = (kind, angle)
        if key not in self._sprites:
            self._sprites[key] = pygame.transform.rotate(make_topping(kind), angle)
        return self._sprites[key]

    def _hand_pos(self, named, side):
        for part in ("idx", "wr"):
            p = named.get(f"{side}_{part}")
            if p is not None:
                return p
        return None

    def _place(self, kind, pos):
        if len(self.toppings) >= MAX_TOPPINGS:
            self.ctx.play("boing")
            return False
        cx, cy = self.center
        dx, dy = pos[0] - cx + random.uniform(-14, 14), pos[1] - cy + random.uniform(-14, 14)
        d = math.hypot(dx, dy)
        lim = R - 34
        if d > lim:
            dx, dy = dx / d * lim, dy / d * lim
        sprite = self._sprite(kind, random.choice(range(0, 360, 30)))
        self.toppings.append((kind, cx + dx, cy + dy, sprite))
        self.ctx.play("poof")
        self.particles.burst((cx + dx, cy + dy), 8, [(255, 255, 255), (255, 232, 140)],
                             160, 0.45, (2, 5), 300)
        return True

    # ---- Ablauf ----
    def play_update(self, dt, pose, hands):
        self.phase_t += dt
        if self.phase == "bake":
            if self.phase_t < BAKE_TIME * 0.8 and random.random() < 0.6:
                self.particles.burst((self.center[0] + random.uniform(-120, 120), self.center[1] - 60),
                                     1, [(255, 255, 255), (240, 240, 245)], 40, 1.0, (6, 12), -80)
            if self.phase_t >= BAKE_TIME:
                self.ctx.play("chime")
                kinds = len({t[0] for t in self.toppings})
                score = len(self.toppings) + 3 * kinds
                self.finish(1 + min(4, score // 8))
            return

        self.timer += dt
        named = dict(pose.named_hand_points()) if pose else {}

        if self.held:
            h = self.held
            h["t"] += dt
            pos = self._hand_pos(named, h["side"])
            if h["t"] > HOLD_TIMEOUT:
                self.held = None
            elif pos is not None:
                cx, cy = self.center
                over = math.hypot(pos[0] - cx, pos[1] - cy) < R - 10
                t_last, p_last = self.last_drop
                moved = p_last is None or math.hypot(pos[0] - p_last[0], pos[1] - p_last[1]) >= DROP_DIST
                if over and self.t - t_last >= DROP_GAP and moved:
                    if self._place(h["kind"], pos):
                        h["left"] -= 1
                        self.last_drop = (self.t, pos)
                    if h["left"] <= 0:
                        self.held = None
        else:
            for b in self.bins:
                side = None
                for s in "lr":
                    p = self._hand_pos(named, s)
                    if p is not None and math.hypot(p[0] - b.c[0], p[1] - b.c[1]) <= b.r * 1.15:
                        side = s
                        break
                b.hover = side is not None
                if not b.hover:
                    b.armed = True
                    b.progress = max(0.0, b.progress - dt * 2)
                elif b.armed:
                    b.progress += dt / PICK_TIME
                    if b.progress >= 1.0:
                        b.progress, b.armed = 0.0, False
                        self.held = dict(kind=b.kind, side=side, left=DROPS_PER_PICK, t=0.0)
                        self.last_drop = (-9.0, None)
                        self.ctx.play("click")

        if self.oven.update(dt, list(named.values())) and self.toppings:
            self._start_bake()
        elif self.timer >= MAX_TIME:
            self._start_bake()

    def _start_bake(self):
        self.phase, self.phase_t, self.held = "bake", 0.0, None
        self.ctx.play("whoosh")

    # ---- Zeichnen ----
    def _draw_pizza(self, surf, scale=1.0, baked=False, dy=0.0):
        base = pizza_base()
        cx, cy = self.center[0], self.center[1] + dy
        if scale == 1.0:
            surf.blit(base, base.get_rect(center=(cx, cy)))
            for kind, x, y, sprite in self.toppings:
                surf.blit(sprite, sprite.get_rect(center=(x, y + dy)))
            if baked:
                ov = baked_overlay()
                surf.blit(ov, ov.get_rect(center=(cx, cy)))
            return
        tmp = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        c = base.get_width() // 2
        tmp.blit(base, (0, 0))
        for kind, x, y, sprite in self.toppings:
            tmp.blit(sprite, sprite.get_rect(center=(c + x - self.center[0], c + y - self.center[1])))
        if baked:
            tmp.blit(baked_overlay(), (0, 0))
        w = max(2, int(tmp.get_width() * scale))
        tmp = pygame.transform.smoothscale(tmp, (w, w))
        surf.blit(tmp, tmp.get_rect(center=(cx, cy)))

    def play_draw(self, surf, pose):
        if self.phase == "bake":
            k = self.phase_t / BAKE_TIME
            veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            veil.fill((60, 20, 10, int(110 + 60 * k)))
            surf.blit(veil, (0, 0))
            glow = 0.5 + 0.5 * math.sin(self.phase_t * 9)
            circle_alpha(surf, (255, 150, 40, int(70 + 50 * glow)), self.center, R + 60 + 14 * glow)
            self._draw_pizza(surf, scale=1.0 - 0.06 * math.sin(k * math.pi), baked=k > 0.5)
            return

        self._draw_pizza(surf)
        for b in self.bins:
            r = int(b.r * (1.08 if b.hover else 1.0) * (1 + 0.02 * math.sin(self.t * 3 + b.c[1])))
            circle_alpha(surf, (255, 255, 255, 170 if b.hover else 120), b.c, r)
            pygame.draw.circle(surf, (255, 255, 255), b.c, r, 5)
            spr = pygame.transform.smoothscale(b.sprite, (int(r * 1.25), int(r * 1.25)))
            surf.blit(spr, spr.get_rect(center=b.c))
            draw_ring(surf, b.c, r + 13, r + 5, b.progress, (255, 225, 60))
        self.oven.draw(surf, self.t)

        if self.held and pose:
            named = dict(pose.named_hand_points())
            pos = self._hand_pos(named, self.held["side"])
            if pos is not None:
                k = ease_out_back(self.held["t"] / 0.25)
                spr = self._sprite(self.held["kind"], 0)
                size = int(S * 1.5 * k)
                if size > 4:
                    big = pygame.transform.smoothscale(spr, (size, size))
                    bob = 5 * math.sin(self.t * 9)
                    surf.blit(big, big.get_rect(center=(pos[0], pos[1] - 34 + bob)))
                    for i in range(self.held["left"]):       # übrige Portionen als Punkte
                        pygame.draw.circle(surf, (255, 225, 60),
                                           (int(pos[0] - (self.held["left"] - 1) * 8 + i * 16), int(pos[1] - 88)), 5)

    def result_draw(self, surf):
        k = ease_out_back(self.state_t / 0.7)
        self.center = (self.W * 0.5, self.H * 0.60)        # no bottom buttons any more: room for a big pizza
        self._draw_pizza(surf, scale=max(0.05, 0.80 * k), baked=True)

