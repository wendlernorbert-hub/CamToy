"""Spiel 1: Seifenblasen - mit den Händen platzen lassen (Wishi-Washi/Bubble-Pop-Gefühl)."""
import math
import random

import pygame

from .common import (Game, circle_alpha, draw_star, draw_stars_row, rainbow, text)

LEVELS = {1: dict(r=(70, 100), vy=(55, 95), maxn=6, every=0.9),
          2: dict(r=(52, 80), vy=(85, 135), maxn=8, every=0.65),
          3: dict(r=(40, 62), vy=(120, 190), maxn=10, every=0.45)}


def make_sprite(r, hue, gold):
    col = (255, 214, 60) if gold else rainbow(hue, 8, 0.45)
    surf = pygame.Surface((2 * r + 10, 2 * r + 10), pygame.SRCALPHA)
    c = (r + 5, r + 5)
    pygame.draw.circle(surf, col + (80,), c, r)
    pygame.draw.circle(surf, (255, 255, 255, 190), c, r, 4)
    pygame.draw.circle(surf, col + (170,), c, r - 6, 3)
    hl = pygame.Rect(0, 0, int(r * .55), int(r * .3))
    hl.center = (int(c[0] - r * .38), int(c[1] - r * .46))
    pygame.draw.ellipse(surf, (255, 255, 255, 235), hl)
    pygame.draw.circle(surf, (255, 255, 255, 200), (int(c[0] + r * .45), int(c[1] + r * .38)), max(2, int(r * .08)))
    if gold:
        draw_star(surf, c, r * .55, (255, 255, 255), outline=(230, 150, 0))
    return surf


class Bubble:
    def __init__(self, x, y, r, vy, hue, gold=False):
        self.x, self.y, self.r, self.vy = x, y, r, vy
        self.ph = random.uniform(0, 6.28)
        self.amp = random.uniform(12, 32)
        self.x0 = x
        self.gold = gold
        self.sprite = make_sprite(int(r), hue, gold)

    @property
    def pos(self):
        return (self.x, self.y)


class BubbleGame(Game):
    title = "Seifenblasen"
    speech = "Seifenblasen! Platze sie mit deinen Händen!"
    DURATION = 45.0

    @staticmethod
    def icon(surf, c, r):
        for dx, dy, k, h in ((-.35, .15, .55, 0), (.3, -.25, .45, 3), (.25, .4, .35, 5)):
            s = make_sprite(int(r * k), h, False)
            surf.blit(s, (c[0] + dx * r - s.get_width() / 2, c[1] + dy * r - s.get_height() / 2))

    def on_restart(self):
        self.bubbles, self.rings = [], []
        self.score, self.timer, self.idle = 0, 0.0, 0.0
        self.spawn_t, self.gold_t = 0.2, random.uniform(9, 14)

    def spawn(self, near=None, gold=False):
        lv = LEVELS[self.ctx.level]
        r = random.uniform(*lv["r"]) * (1.15 if gold else 1.0)
        x = random.uniform(r + 30, self.W - r - 30)
        y = self.H + r + 5
        if near:
            x = min(max(near[0] + random.uniform(-90, 90), r + 20), self.W - r - 20)
            y = min(self.H + r, near[1] + 260)
        self.bubbles.append(Bubble(x, y, r, random.uniform(*lv["vy"]) * (0.8 if gold else 1.0),
                                   random.randint(0, 7), gold))

    def pop(self, b, silent=False):
        if b not in self.bubbles:
            return
        self.bubbles.remove(b)
        self.score += 1
        self.idle = 0.0
        cols = [rainbow(random.randint(0, 7), 8, .5) for _ in range(4)] + [(255, 255, 255)]
        self.particles.burst(b.pos, 16, cols, 260, 0.6, (3, 8), 400)
        self.rings.append([b.x, b.y, b.r, 0.0])
        if not silent:
            self.ctx.play("gold" if b.gold else "pop")
        if b.gold:
            self.particles.burst(b.pos, 40, [(255, 214, 40), (255, 255, 255)], 480, 1.0, (4, 10), 300, "star")
            for o in list(self.bubbles):
                self.pop(o, silent=True)

    def play_update(self, dt, pose, hands):
        lv = LEVELS[self.ctx.level]
        self.timer += dt
        self.idle += dt
        self.spawn_t -= dt
        if self.spawn_t <= 0 and len(self.bubbles) < lv["maxn"]:
            self.spawn()
            self.spawn_t = lv["every"] * random.uniform(0.7, 1.3)
        self.gold_t -= dt
        if self.gold_t <= 0:
            self.spawn(gold=True)
            self.gold_t = random.uniform(10, 16)
        for b in self.bubbles:
            b.y -= b.vy * dt
            b.x = b.x0 + math.sin(self.t * 1.6 + b.ph) * b.amp
        self.bubbles = [b for b in self.bubbles if b.y > -b.r - 20]
        for b in list(self.bubbles):
            if b in self.bubbles and any(math.hypot(x - b.x, y - b.y) < b.r + 12 for x, y in hands):
                self.pop(b)
        for ring in self.rings:
            ring[3] += dt
        self.rings = [r for r in self.rings if r[3] < 0.35]
        if self.idle > 6 and hands:           # sanfte Hilfe: Blase zur Hand schicken
            self.spawn(near=hands[0])
            self.idle = 3.0
        if self.timer >= self.DURATION:
            self.finish(1 + self.score // 8)

    def play_draw(self, surf, pose):
        for b in self.bubbles:
            surf.blit(b.sprite, (b.x - b.sprite.get_width() / 2, b.y - b.sprite.get_height() / 2))
        for x, y, r, t in self.rings:
            k = t / 0.35
            circle_alpha(surf, (255, 255, 255, int(200 * (1 - k))), (x, y), r * (1 + 0.5 * k), 4)
        if self.state == "play":
            draw_stars_row(surf, (self.W / 2, 52), 10, min(10, self.score // 3), 30)
            w = 340
            x0, y0 = self.W / 2 - w / 2, 92
            pygame.draw.rect(surf, (255, 255, 255), (x0 - 3, y0 - 3, w + 6, 18), border_radius=9)
            pygame.draw.rect(surf, (80, 190, 255), (x0, y0, w * max(0, 1 - self.timer / self.DURATION), 12),
                             border_radius=6)

    def result_draw(self, surf):
        pass                                          # the stars on top say it all
