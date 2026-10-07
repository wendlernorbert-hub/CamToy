"""Spiel 4: Kung-Fu-Meister - Ninja-Köpfe und Holzbretter treffen (Whack-a-Mole mit Körper).

Level 1: einfach berühren. Level 2/3: Hand muss schnell sein (echter "Schlag"),
Holzbretter unten verlangen Tritte (nur wenn die Füße sichtbar sind).
Am Ende gibt es einen Gürtel in Weiß bis Schwarz.
"""
import math
import random
from collections import deque

import pygame

from common import (Game, ease_out_back, draw_stars_row, ellipse_pts, poly_alpha, star_pts, text)

LEVELS = {1: dict(life=3.4, n=2, speed=0, every=0.9, r=64),
          2: dict(life=2.5, n=3, speed=260, every=0.7, r=54),
          3: dict(life=1.9, n=3, speed=430, every=0.5, r=46)}
HAND_SPOTS = [(.13, .30), (.87, .30), (.11, .58), (.89, .58), (.22, .17), (.78, .17),
              (.21, .44), (.79, .44), (.30, .27), (.70, .27)]
BOARD_SPOTS = [(.22, .88), (.78, .88)]
BELTS = [(0, (245, 245, 245), "Weißer Gürtel"), (4, (250, 220, 60), "Gelber Gürtel"),
         (8, (250, 150, 40), "Oranger Gürtel"), (13, (80, 190, 90), "Grüner Gürtel"),
         (18, (70, 130, 230), "Blauer Gürtel"), (24, (140, 90, 50), "Brauner Gürtel"),
         (30, (35, 35, 40), "Schwarzer Gürtel")]


def belt_index(score):
    return max(i for i, (need, _, _) in enumerate(BELTS) if score >= need)


def draw_ninja(surf, c, r, t):
    x, y = c
    pygame.draw.circle(surf, (40, 40, 70), (int(x), int(y)), int(r))
    pygame.draw.circle(surf, (15, 15, 30), (int(x), int(y)), int(r), 3)
    pygame.draw.polygon(surf, (245, 205, 160), ellipse_pts(x, y - .02 * r, .8 * r, .32 * r))
    for s in (-1, 1):
        pygame.draw.polygon(surf, (255, 255, 255), ellipse_pts(x + s * .32 * r, y - .02 * r, .17 * r, .13 * r))
        pygame.draw.circle(surf, (20, 20, 30), (int(x + s * .32 * r), int(y - .01 * r)), max(2, int(.075 * r)))
        pygame.draw.line(surf, (20, 20, 30), (x + s * .52 * r, y - .22 * r), (x + s * .1 * r, y - .12 * r), max(3, int(.07 * r)))
    pygame.draw.polygon(surf, (230, 50, 60), [(x - .785 * r, y - .62 * r), (x + .785 * r, y - .62 * r),
                                             (x + .908 * r, y - .42 * r), (x - .908 * r, y - .42 * r)])
    fl = math.sin(t * 9) * .12 * r
    pygame.draw.polygon(surf, (230, 50, 60), [(x + .85 * r, y - .55 * r), (x + 1.5 * r, y - .8 * r + fl), (x + 1.25 * r, y - .45 * r)])
    pygame.draw.polygon(surf, (230, 50, 60), [(x + .85 * r, y - .5 * r), (x + 1.45 * r, y - .3 * r - fl), (x + 1.2 * r, y - .55 * r)])
    pygame.draw.arc(surf, (140, 60, 50), (x - .22 * r, y + .12 * r, .44 * r, .3 * r), math.pi * 1.1, math.pi * 1.9, 3)


def draw_board(surf, c, r, rot=0.0, half=0):
    w, h = 1.0 * r, .46 * r
    c0, s0 = math.cos(rot), math.sin(rot)

    def tr(px, py):
        return (c[0] + px * c0 - py * s0, c[1] + px * s0 + py * c0)
    x0, x1 = (-w, w) if half == 0 else ((-w, 0) if half < 0 else (0, w))
    pts = [tr(x0, -h), tr(x1, -h), tr(x1, h), tr(x0, h)]
    pygame.draw.polygon(surf, (205, 150, 85), pts)
    pygame.draw.polygon(surf, (110, 70, 35), pts, 4)
    for k in (-.4, 0, .4):
        pygame.draw.line(surf, (160, 105, 55), tr(x0, k * h), tr(x1, k * h), 2)


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
    def __init__(self, pos, kind, life):
        self.x, self.y = pos
        self.kind, self.life, self.age = kind, life, 0.0
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
        return (self.x, self.y)


class KungFuGame(Game):
    title = "Kung-Fu-Meister"
    speech = "Kung Fu! Hau die Ninjas mit Händen und Füßen!"
    DURATION = 45.0

    @staticmethod
    def icon(surf, c, r):
        draw_ninja(surf, c, r * .85, 0)

    def on_restart(self):
        self.targets, self.pows = [], []
        self.score, self.timer, self.spawn_t = 0, 0.0, 0.5
        self.combo, self.last_hit = 0, -9.0
        self.hist = {}
        self.belt = 0

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
        feet = pose.foot_points(0.5) if pose else {}
        have_legs = bool(pose) and pose.has("l_an", "r_an", thr=0.5)
        named = dict(pose.named_hand_points()) if pose else {}
        speeds = self._speeds({**named, **{k: v for k, v in feet.items() if k.endswith("_an")}})
        self.spawn_t -= dt
        active = [t for t in self.targets if not t.hit]
        if self.spawn_t <= 0 and len(active) < lv["n"]:
            board = self.ctx.level >= 2 and have_legs and random.random() < 0.25
            p = self._free_spot(list(BOARD_SPOTS if board else HAND_SPOTS))
            if p:
                self.targets.append(Target(p, "board" if board else "ninja", lv["life"] * (1.2 if board else 1.0)))
                self.ctx.play("whoosh")
            self.spawn_t = lv["every"] * random.uniform(0.7, 1.3)
        for tg in self.targets:
            tg.age += dt
            if tg.hit:
                tg.hit_t += dt
                continue
            if tg.age < 0.3:
                continue
            pts = (feet if tg.kind == "board" else named)
            for n, (x, y) in pts.items():
                if tg.kind == "board" and not n.endswith("_an"):
                    continue
                reach = (lv["r"] + 14) if tg.kind == "ninja" else 78
                if math.hypot(x - tg.x, y - tg.y) < reach and speeds.get(n, 0) >= lv["speed"] * (0.6 if tg.kind == "board" else 1):
                    self.hit(tg)
                    break
            if not tg.hit and tg.age > tg.life:
                tg.age = 1e9
                self.ctx.play("down")
        self.targets = [t for t in self.targets if (t.age < t.life and not t.hit) or (t.hit and t.hit_t < 0.7)]
        self.pows = [(p[0], p[1], p[2] + dt) for p in self.pows if p[2] < 0.3]
        if self.timer >= self.DURATION:
            self.finish(1 + (belt_index(self.score) * 4) // 6)

    def hit(self, tg):
        tg.hit = True
        self.score += 1
        self.combo = self.combo + 1 if self.t - self.last_hit < 1.6 else 1
        self.last_hit = self.t
        self.ctx.play("board" if tg.kind == "board" else "hit")
        self.pows.append((tg.x, tg.y, 0.0))
        cols = [(255, 230, 80), (255, 140, 60), (255, 255, 255)]
        self.particles.burst((tg.x, tg.y), 22 + 6 * min(self.combo, 5), cols, 420, .7, (4, 10), 500, "star")
        b = belt_index(self.score)
        if b != self.belt:
            self.belt = b
            self.ctx.play("cheer")
            self.ctx.say("Neuer Gürtel!")
            self.particles.confetti(self.W, 40)

    def play_draw(self, surf, pose):
        for tg in self.targets:
            sc = tg.scale()
            if sc <= 0.02:
                continue
            x, y = tg.pos()
            if tg.kind == "ninja":
                poly_alpha(surf, (0, 0, 0, 70), ellipse_pts(tg.x, tg.y + .95 * LEVELS[self.ctx.level]["r"], 70 * sc, 16 * sc))
                draw_ninja(surf, (x, y), LEVELS[self.ctx.level]["r"] * sc, self.t)
            elif tg.hit:
                r = 74 * sc
                draw_board(surf, (x - 20 * tg.hit_t * 60, y), r, -tg.hit_t * 4, -1)
                draw_board(surf, (x + 20 * tg.hit_t * 60, y), r, tg.hit_t * 4, 1)
            else:
                draw_board(surf, (x, y), 74 * sc)
        for x, y, t in self.pows:
            k = t / 0.3
            pygame.draw.polygon(surf, (255, 235, 60), star_pts((x, y), 110 * (0.5 + k), k, .5, 8))
            pygame.draw.polygon(surf, (230, 60, 40), star_pts((x, y), 110 * (0.5 + k), k, .5, 8), 6)
            text(surf, "POW!", 54, (x, y), (230, 50, 40))
        if self.state == "play":
            draw_stars_row(surf, (self.W / 2, 52), 10, min(10, self.score // 3), 30)
            w = 340
            x0, y0 = self.W / 2 - w / 2, 92
            pygame.draw.rect(surf, (255, 255, 255), (x0 - 3, y0 - 3, w + 6, 18), border_radius=9)
            pygame.draw.rect(surf, (255, 140, 60), (x0, y0, w * max(0, 1 - self.timer / self.DURATION), 12), border_radius=6)
            draw_belt(surf, (self.W - 110, 62), 120, BELTS[self.belt][1])
            if self.combo >= 3 and self.t - self.last_hit < 1.2:
                text(surf, "x%d" % self.combo, 70, (self.W / 2, self.H * 0.7), (255, 230, 70))

    def result_draw(self, surf):
        b = belt_index(self.score)
        k = ease_out_back(self.state_t / 0.8)
        draw_belt(surf, (self.W // 2, self.H * 0.43), 380 * k, BELTS[b][1])
        text(surf, BELTS[b][2], 46, (self.W // 2, self.H * 0.66))
        text(surf, "%d Treffer" % self.score, 38, (self.W // 2, self.H * 0.72))
