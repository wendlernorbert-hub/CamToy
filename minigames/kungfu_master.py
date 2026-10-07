"""Spiel 4: Kung-Fu-Meister - das Kind wird zum blauen Ninja und haut rote Ninjas weg.

Whack-a-Mole mit dem Körper. Level 1: einfach berühren. Level 2/3: die Hand muss schnell sein
(echter "Schlag"). Holzbretter unten verlangen Tritte (nur wenn die Füße sichtbar sind).
Zwischendurch taucht ein Boss-Ninja auf, der mehrere Treffer braucht. Am Ende gibt es einen
Gürtel in Weiß bis Schwarz. Kein Verlieren: ein entkommener Ninja kostet nichts.
"""
import math
import random
from collections import deque

import pygame

from .common import (Game, circle_alpha, ease_out_back, draw_stars_row, ellipse_pts, heart_pts,
                     poly_alpha, star_pts, text)
from .costumes import Xf

LEVELS = {1: dict(life=3.4, n=2, speed=0, every=0.9, r=64),
          2: dict(life=2.5, n=3, speed=260, every=0.7, r=54),
          3: dict(life=1.9, n=3, speed=430, every=0.5, r=46)}
HAND_SPOTS = [(.13, .30), (.87, .30), (.11, .58), (.89, .58), (.22, .17), (.78, .17),
              (.21, .44), (.79, .44), (.30, .27), (.70, .27)]
BOARD_SPOTS = [(.22, .88), (.78, .88)]
# boss ninja: hits needed, seconds on screen, kills of normal ninjas between two bosses
BOSS = {1: dict(hp=3, life=9.0, every=8), 2: dict(hp=4, life=8.0, every=7), 3: dict(hp=5, life=7.0, every=6)}
BOSS_SIZE = 1.65               # boss radius = normal radius * this
BOSS_MIN_SPEED = 150.0         # px/s: even on level 1 the boss needs a real swing
BOSS_COOLDOWN = 0.55           # seconds between two hits that count (one swing = one hit)
BOSS_KILL_POINTS = 5
BLUE = (60, 130, 240)
BLUE_DARK = (30, 70, 170)
BELTS = [(0, (245, 245, 245), "Weißer Gürtel"), (4, (250, 220, 60), "Gelber Gürtel"),
         (8, (250, 150, 40), "Oranger Gürtel"), (13, (80, 190, 90), "Grüner Gürtel"),
         (18, (70, 130, 230), "Blauer Gürtel"), (24, (140, 90, 50), "Brauner Gürtel"),
         (30, (35, 35, 40), "Schwarzer Gürtel")]


def belt_index(score):
    return max(i for i, (need, _, _) in enumerate(BELTS) if score >= need)


def draw_ninja(surf, c, r, t, style="red", flash=0.0):
    """Enemy ninja. style: "red" (normal) or "boss" (crimson, golden band, horns)."""
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
    pygame.draw.arc(surf, (140, 60, 50), (x - .22 * r, y + .12 * r, .44 * r, .3 * r), math.pi * 1.1, math.pi * 1.9, 3)
    if boss:                                           # fangs
        for sd in (-1, 1):
            pygame.draw.polygon(surf, (255, 255, 255), [(x + sd * .12 * r, y + .2 * r),
                                (x + sd * .24 * r, y + .2 * r), (x + sd * .18 * r, y + .4 * r)])
    if flash > 0:                                      # white flash when hit
        circle_alpha(surf, (255, 255, 255, int(200 * min(1.0, flash))), (x, y), r)


# ---------------------------------------------------------------- Der blaue Ninja ---

def draw_player_ninja(surf, pose, t):
    """Dresses the player as a blue ninja: forehead hood + headband with fluttering tails,
    a face mask below the eyes, and a scarf at the neck. Eyes stay visible."""
    if not pose or not pose.ok:
        return
    head = pose.head()
    if head:
        eye_mid, hs, tilt = head
        # the ear landmarks wander when the head is turned or tilted: a head is about
        # 1.9 - 3.1 eye distances wide, so keep the costume inside that range
        eye_d = float(math.hypot(*(pose.P("l_eye") - pose.P("r_eye"))))
        if eye_d > 4:
            hs = min(max(hs, 1.9 * eye_d), 3.1 * eye_d)
        xf = Xf(eye_mid[0], eye_mid[1], hs, tilt)
        # hood over hair and forehead
        pygame.draw.polygon(surf, BLUE, xf.ell(0, -.32, .6, .42, 0, 26))
        pygame.draw.polygon(surf, BLUE_DARK, xf.ell(0, -.32, .6, .42, 0, 26), 3)
        # headband with a metal plate and two tails that flutter behind
        pygame.draw.polygon(surf, BLUE_DARK, xf.pts([(-.58, -.2), (.58, -.2), (.6, -.04), (-.6, -.04)]))
        pygame.draw.polygon(surf, (225, 232, 245), xf.pts([(-.16, -.2), (.16, -.2), (.16, -.04), (-.16, -.04)]))
        pygame.draw.polygon(surf, BLUE_DARK, xf.pts([(-.16, -.2), (.16, -.2), (.16, -.04), (-.16, -.04)]), 2)
        for k, (dy, lng) in enumerate(((-.17, 1.0), (-.08, .8))):
            w = math.sin(t * 8 + k * 1.7) * .09
            pygame.draw.polygon(surf, BLUE_DARK, xf.pts([
                (.56, dy - .05), (.56 + lng * .55, dy - .22 + w), (.56 + lng * .9, dy + .1 + w * 1.4),
                (.56 + lng * .42, dy + .06), (.56, dy + .06)]))
        # face mask below the eyes (eyes + nose bridge stay free)
        mask = [(-.54, .2), (-.28, .13), (0, .17), (.28, .13), (.54, .2),
                (.46, .62), (0, .86), (-.46, .62)]
        pygame.draw.polygon(surf, BLUE, xf.pts(mask))
        pygame.draw.polygon(surf, BLUE_DARK, xf.pts(mask), 3)
        pygame.draw.line(surf, BLUE_DARK, xf.pt(-.3, .62), xf.pt(.3, .62), max(2, xf.r(.03)))
    if pose.has("l_sh", "r_sh", thr=0.4):
        # a small scarf at the neck: narrow and flat, so it never covers the face even when
        # the head is bent forward
        l, r = pose.P("l_sh"), pose.P("r_sh")
        sm, w = (l + r) / 2, float(math.hypot(*(r - l)))
        ang = math.atan2(r[1] - l[1], r[0] - l[0])
        xs = Xf(sm[0], sm[1] - w * .05, w, ang)
        scarf = [(-.24, -.03), (-.1, -.09), (.1, -.09), (.24, -.03), (.21, .07), (.08, .12), (-.08, .12), (-.21, .07)]
        pygame.draw.polygon(surf, BLUE, xs.pts(scarf))
        pygame.draw.polygon(surf, BLUE_DARK, xs.pts(scarf), 3)
        sway = math.sin(t * 5) * .04                     # loose scarf end
        pygame.draw.polygon(surf, BLUE_DARK, xs.pts([(.14, .08), (.27 + sway, .3), (.35 + sway, .27), (.22, .04)]))


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

    @staticmethod
    def icon(surf, c, r):
        draw_ninja(surf, c, r * .85, 0)

    def on_restart(self):
        self.targets, self.pows = [], []
        self.score, self.timer, self.spawn_t = 0, 0.0, 0.5
        self.combo, self.last_hit = 0, -9.0
        self.hist = {}
        self.belt = 0
        self.kills_since_boss = 0
        self.boss_banner = 0.0

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
            board = self.ctx.level >= 2 and have_legs and random.random() < 0.25
            p = self._free_spot(list(BOARD_SPOTS if board else HAND_SPOTS))
            if p:
                self.targets.append(Target(p, "board" if board else "ninja", lv["life"] * (1.2 if board else 1.0)))
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
            pts = (feet if tg.kind == "board" else named)
            for n, (x, y) in pts.items():
                if tg.kind == "board" and not n.endswith("_an"):
                    continue
                if tg.kind == "boss":
                    reach = lv["r"] * BOSS_SIZE + 14
                elif tg.kind == "ninja":
                    reach = lv["r"] + 14
                else:
                    reach = 78
                need = lv["speed"] * (0.6 if tg.kind == "board" else 1)
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
        if tg.kind == "ninja":
            self.kills_since_boss += 1
        self._check_belt()

    def _check_belt(self):
        b = belt_index(self.score)
        if b != self.belt:
            self.belt = b
            self.ctx.play("cheer")
            self.ctx.say("Neuer Gürtel!")
            self.particles.confetti(self.W, 40)

    def hit_boss(self, tg):
        """A boss needs several hits: it shakes and flashes, only the last one knocks it out."""
        tg.hp -= 1
        tg.last_hit, tg.flash, tg.shake = self.t, 0.25, 0.3
        self.score += 1
        self.combo = self.combo + 1 if self.t - self.last_hit < 1.6 else 1
        self.last_hit = self.t
        self.pows.append((tg.x, tg.y, 0.0))
        cols = [(255, 230, 80), (255, 140, 60), (255, 255, 255)]
        if tg.hp > 0:
            self.ctx.play("board")
            self.particles.burst((tg.x, tg.y), 14, cols, 330, .5, (3, 8), 500, "star")
        else:
            tg.hit = True                                   # knocked out: flies away like the others
            self.score += BOSS_KILL_POINTS
            self.ctx.play("cheer")
            self.ctx.say("Boss besiegt!")
            self.particles.burst((tg.x, tg.y), 50, cols, 520, .9, (5, 12), 450, "star")
            self.particles.confetti(self.W, 60)
        self._check_belt()

    def play_draw(self, surf, pose):
        draw_player_ninja(surf, pose, self.t)               # the player is the blue ninja
        for tg in self.targets:
            sc = tg.scale()
            if sc <= 0.02:
                continue
            x, y = tg.pos()
            if tg.kind == "boss":
                r = LEVELS[self.ctx.level]["r"] * BOSS_SIZE * sc
                poly_alpha(surf, (0, 0, 0, 80), ellipse_pts(tg.x, tg.y + .95 * r, 1.2 * r, 20 * sc))
                draw_ninja(surf, (x, y), r, self.t, "boss", tg.flash / 0.25)
                if not tg.hit:                              # hearts = hits left
                    for i in range(tg.max_hp):
                        hx = tg.x + (i - (tg.max_hp - 1) / 2) * 36 * sc
                        hy = tg.y - r * 1.75
                        pts = heart_pts((hx, hy), 15 * sc)
                        if i < tg.hp:
                            pygame.draw.polygon(surf, (235, 50, 70), pts)
                        pygame.draw.polygon(surf, (255, 255, 255) if i < tg.hp else (190, 190, 205), pts, 3)
            elif tg.kind == "ninja":
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
            if self.boss_banner > 0:
                k = ease_out_back(min(1.0, (1.8 - self.boss_banner) / 0.35))
                text(surf, "BOSS!", int(130 * k), (self.W / 2 + random.uniform(-4, 4), self.H * 0.30),
                     (255, 70, 70))

    def result_draw(self, surf):
        b = belt_index(self.score)
        k = ease_out_back(self.state_t / 0.8)
        draw_belt(surf, (self.W // 2, self.H * 0.43), 380 * k, BELTS[b][1])

