"""Spiel 1: Seifenblasen - mit den Händen platzen lassen (Wishi-Washi/Bubble-Pop-Gefühl)."""
import math
import random

import numpy as np
import pygame

import gfx
from .common import POP_PITCHES, Game, circle_alpha, rainbow, star_sprite

# r: smallest/biggest radius, speed: how fast they come in, turb: how wild the wind swirls them
LEVELS = {1: dict(r=(26, 110), speed=0.8, turb=150, maxn=9, every=0.55),
          2: dict(r=(22, 96), speed=1.1, turb=210, maxn=11, every=0.45),
          3: dict(r=(18, 84), speed=1.4, turb=280, maxn=13, every=0.35)}
# now and then a bubble far outside that range: tiny (extra high pop) or a giant (extra deep pop)
# that bursts into a few little ones
TINY_R, TINY_CHANCE = (10, 16), 0.10
GIANT_R, GIANT_CHANCE = (140, 170), 0.06


def _bubble(r, hue, gold):
    """Soap bubble: see-through middle, shimmering rainbow film at the rim, window reflections."""
    n = 2 * r + 6
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    u, v = (xx - n / 2 + .5) / r, (yy - n / 2 + .5) / r
    d = np.sqrt(u * u + v * v)
    ang = np.arctan2(v, u)
    inside = np.clip((1 - d) * r + .5, 0, 1)
    rim = np.clip((d - .45) / .55, 0, 1) ** 2.4
    film = hue / 8 + 0.18 * np.sin(ang * 2 + d * 5) + 0.25 * d          # thin-film colour sweep
    irid = 0.5 + 0.5 * np.cos(2 * np.pi * (film[..., None] + np.array([0, .33, .67], np.float32)))
    base = np.array((255, 205, 60) if gold else rainbow(hue, 8, .55), np.float32) / 255
    rgb = (base * 0.55 + irid * 0.45) * 255
    alpha = 0.10 + 0.72 * rim + (0.25 if gold else 0)
    edge = np.clip(1 - np.abs(d - .955) * r / 2.2, 0, 1)                   # crisp outer line
    win = np.clip(1 - np.hypot((u + .36) / .34, (v + .42) / .2), 0, 1) ** .6   # window reflection
    dot = np.clip(1 - np.hypot(u - .42, v - .4) / .09, 0, 1)
    glint = np.clip(np.maximum(np.maximum(edge * .75, win * .95), dot * .9), 0, 1)
    rgb = rgb * (1 - glint[..., None]) + 255 * glint[..., None]
    alpha = np.clip(np.maximum(alpha, glint), 0, 1) * inside
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(s)[...] = np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2)
    pygame.surfarray.pixels_alpha(s)[...] = (alpha * 255).astype(np.uint8).T
    if gold:
        gfx.blit_center(s, star_sprite(r * .5), (n / 2, n / 2))
    return s


def make_sprite(r, hue, gold):
    r = max(8, int(r) // 4 * 4)                    # a handful of sizes, so they can be made in advance
    return gfx.cached(("bubble", r, hue, gold), lambda: _bubble(r, hue, gold))


class Bubble:
    def __init__(self, x, y, r, vx, vy, hue):
        self.x, self.y, self.r, self.vx, self.vy = x, y, r, vx, vy
        self.ph = random.uniform(0, 6.28)
        self.age = 0.0
        self.sprite = make_sprite(int(r), hue, False)

    @property
    def pos(self):
        return (self.x, self.y)


class BubbleGame(Game):
    """Free play: no score, no clock - bubbles just keep coming until the home button."""
    title = "Seifenblasen"
    speech = "Seifenblasen! Platze sie mit deinen Händen!"
    rounds = False

    @staticmethod
    def icon(surf, c, r):
        for dx, dy, k, h in ((-.35, .15, .55, 0), (.3, -.25, .45, 3), (.25, .4, .35, 5)):
            s = _bubble(max(4, int(r * k)), h, False)
            surf.blit(s, (c[0] + dx * r - s.get_width() / 2, c[1] + dy * r - s.get_height() / 2))

    def on_restart(self):
        self.bubbles, self.rings = [], []
        self.score, self.idle = 0, 0.0
        self.spawn_t = 0.2

    def spawn(self, near=None):
        """New bubble from below or from a side, with a random size (small ones are common)."""
        lv = LEVELS[self.ctx.level]
        lo, hi = lv["r"]
        r = lo + (hi - lo) * random.random() ** 1.4
        sp = lv["speed"]
        roll = random.random()
        if not near and roll < TINY_CHANCE:            # now and then a tiny one ...
            r = random.uniform(*TINY_R)
        elif not near and roll < TINY_CHANCE + GIANT_CHANCE and not any(b.r >= GIANT_R[0] for b in self.bubbles):
            r, sp = random.uniform(*GIANT_R), sp * 0.6   # ... or a slow giant (one at a time)
        side = random.random()
        if near:                                       # gentle help: one drifts right to the hand
            x = min(max(near[0] + random.uniform(-90, 90), r + 20), self.W - r - 20)
            y = min(self.H + r, near[1] + 220)
            vx, vy = random.uniform(-20, 20), -70 * sp
        elif side < 0.5:                               # from below
            x, y = random.uniform(r + 30, self.W - r - 30), self.H + r + 5
            vx, vy = random.uniform(-60, 60) * sp, random.uniform(-150, -70) * sp
        else:                                          # blown in from the left or right
            d = -1 if side < 0.75 else 1
            x, y = (self.W + r + 5) if d > 0 else (-r - 5), random.uniform(0.15, 0.85) * self.H
            vx, vy = -d * random.uniform(90, 190) * sp, random.uniform(-60, 30) * sp
        self.bubbles.append(Bubble(x, y, r, vx, vy, random.randint(0, 7)))

    def pop(self, b):
        if b not in self.bubbles:
            return
        self.bubbles.remove(b)
        self.score += 1
        self.idle = 0.0
        cols = [rainbow(random.randint(0, 7), 8, .5) for _ in range(4)] + [(255, 255, 255)]
        self.particles.burst(b.pos, 6 + int(b.r / 10), cols, 120 + 2 * b.r, 0.5, (3, 7), 400)
        self.rings.append([b.x, b.y, b.r, 0.0])
        # small bubbles pop high, big ones deep (a little random, so it never sounds the same);
        # the tiny and giant ones get their own extra high / extra deep pop
        if b.r < TINY_R[1] + 1:
            self.ctx.play("pop_tiny")
        elif b.r >= GIANT_R[0]:
            self.ctx.play("pop_giant")
            for _ in range(random.randint(3, 5)):        # a giant bursts into 3-5 little ones
                a = random.uniform(0, 2 * math.pi)
                r, v = random.uniform(18, 34), random.uniform(140, 240)
                self.bubbles.append(Bubble(b.x + math.cos(a) * b.r * 0.4, b.y + math.sin(a) * b.r * 0.4, r,
                                           math.cos(a) * v, math.sin(a) * v - 60, random.randint(0, 7)))
        else:
            lo, hi = 18, 112
            k = (b.r - lo) / (hi - lo) * (POP_PITCHES - 1) + random.uniform(-0.6, 0.6)
            self.ctx.play(f"pop{int(round(min(POP_PITCHES - 1, max(0, k))))}")

    def _wind(self, x, y, ph):
        """Swirling breeze: a smooth field of eddies that slowly changes over time."""
        t = self.t
        fx = math.sin(y * 0.006 + t * 0.7 + ph) + 0.7 * math.sin(x * 0.011 - t * 1.3) \
            + 0.5 * math.sin((x + y) * 0.004 + t * 0.4)
        fy = math.cos(x * 0.007 - t * 0.6 + ph) + 0.7 * math.cos(y * 0.013 + t * 1.1) \
            + 0.5 * math.cos((x - y) * 0.005 - t * 0.5)
        return fx, fy

    def play_update(self, dt, pose, hands):
        lv = LEVELS[self.ctx.level]
        self.idle += dt
        self.spawn_t -= dt
        if self.spawn_t <= 0 and len(self.bubbles) < lv["maxn"]:
            self.spawn()
            self.spawn_t = lv["every"] * random.uniform(0.5, 1.4)
        drag = math.exp(-0.5 * dt)
        for b in self.bubbles:
            b.age += dt
            fx, fy = self._wind(b.x, b.y, b.ph)
            turb = lv["turb"] * (55.0 / b.r) ** 0.6           # small bubbles get thrown around more
            b.vx = b.vx * drag + fx * turb * dt
            b.vy = b.vy * drag + (fy * turb - 22) * dt        # -22: they still drift up a little
            b.x += b.vx * dt
            b.y += b.vy * dt
        m = 40
        self.bubbles = [b for b in self.bubbles
                        if b.age < 25 and (b.age < 2.5 or -b.r - m < b.x < self.W + b.r + m
                                           and -b.r - m < b.y < self.H + b.r + m)]
        for b in list(self.bubbles):
            if b in self.bubbles and any(math.hypot(x - b.x, y - b.y) < b.r + 14 for x, y in hands):
                self.pop(b)
        for ring in self.rings:
            ring[3] += dt
        self.rings = [r for r in self.rings if r[3] < 0.35]
        if self.idle > 6 and hands:           # sanfte Hilfe: Blase zur Hand schicken
            self.spawn(near=hands[0])
            self.idle = 3.0

    def play_draw(self, surf, pose):
        for b in self.bubbles:
            wob = 0.06 * math.sin(self.t * 5 + b.ph)                 # soft wobble
            gfx.blit_center(surf, b.sprite, b.pos, sx=1 + wob, sy=1 - wob)
        for x, y, r, t in self.rings:
            k = t / 0.35
            gfx.add_glow(surf, (x, y), r * (1.2 + k), (200, 230, 255), 0.7 * (1 - k))
            circle_alpha(surf, (255, 255, 255, int(220 * (1 - k))), (x, y), r * (1 + 0.6 * k), max(2, int(6 * (1 - k))))
