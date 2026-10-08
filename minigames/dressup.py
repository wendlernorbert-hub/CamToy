"""Spiel 2: Verkleiden - Hut, Brille, Nase, Umhang, Flügel und Handobjekt wählen.

Die Hand ein Weilchen auf eine Kachel halten = nächstes Teil. Umhang und Flügel
werden (mit Personen-Maske) hinter dem Kind gezeichnet. Foto-Knopf macht ein Bild.
"""
import math
import os
import random
import time

import numpy as np
import pygame

import gfx
from . import costumes as C
from .common import (DwellButton, Game, button_sprite, ease_out_back, progress_ring, text,
                     update_exclusive)
from .costumes import Xf

SLOTS = [("hat", [None, "crown", "wizard", "pirate", "cowboy", "party", "bunny", "chef", "viking", "flowers", "top"]),
         ("glasses", [None, "sun", "heart", "star", "round", "goggles", "mask"]),
         ("face", [None, "clown", "cat", "mustache", "beard", "pig", "dog", "freckles"]),
         ("neck", [None, "bowtie", "pearls", "medal", "tie"]),
         ("back", [None, "red", "fairy", "purple", "butterfly", "bat", "blue", "angel", "dragon", "green"]),
         ("hand", [None, "wand", "sword", "balloon", "flower", "icecream", "lollipop"])]
LOCK = 0.6                     # after a switch, no tile reacts for this long (no double picks)


def icon_camera(surf, c, r):
    x, y = c
    pygame.draw.rect(surf, (60, 60, 80), (x - r, y - r * .55, 2 * r, r * 1.35), border_radius=int(r * .25))
    pygame.draw.rect(surf, (60, 60, 80), (x - r * .4, y - r * .85, r * .8, r * .4), border_radius=4)
    pygame.draw.circle(surf, (230, 235, 250), (int(x), int(y + r * .1)), int(r * .52))
    pygame.draw.circle(surf, (70, 120, 220), (int(x), int(y + r * .1)), int(r * .34))
    pygame.draw.circle(surf, (255, 255, 255), (int(x - r * .1), int(y)), int(r * .1))


class DressUpGame(Game):
    title = "Verkleiden"
    speech = "Verkleide dich! Halte die Hand auf einen Kreis!"
    needs_mask = True
    rounds = False

    @staticmethod
    def icon(surf, c, r):
        xf = Xf(c[0], c[1] + r * .55, r * 1.25)
        C.hat_wizard(surf, xf, 0.5)
        xf2 = Xf(c[0], c[1] + r * .1, r * 1.5)
        C.glasses_sun(surf, xf2, 0)

    def on_restart(self):
        self.sel = {k: 0 for k, _ in SLOTS}
        # every round the pieces come in a new order (so the first hat is not always the crown);
        # "nothing" stays first, then all pieces once, then "nothing" again
        self.order = {k: [None] + random.sample(items[1:], len(items) - 1) for k, items in SLOTS}
        self.tiles = []
        W = self.W
        for i, (key, items) in enumerate(SLOTS):
            left = i < 3
            x = 88 if left else W - 88
            y = 235 + (i % 3) * 150
            self.tiles.append(DwellButton((x, y), 58, 0.75))
        self.btn_photo = DwellButton((W - 58, 58), 40, 1.0, icon=icon_camera)
        self.countdown = None          # Sekunden bis zum Foto
        self.flash = 0.0
        self.thumb, self.thumb_t = None, 0.0
        self._shoot = False
        self.balloon = {}              # slot -> balloon position (it trails behind the hand)
        self.active, self.lock = None, 0.0
        self.ctx.tracker.set_segmentation(True)

    def on_exit(self):
        self.ctx.tracker.set_segmentation(False)

    # ---------------------------------------------------------- Logik ---
    def play_update(self, dt, pose, hands):
        if self.countdown is None:
            # one point per hand (finger, else wrist): wrist + finger used to touch two tiles at once
            pts = [pt for p in (pose.all if pose else []) for pt in p.pointer_points()]
            self.lock = max(0.0, self.lock - dt)
            # only one tile fills at a time (see update_exclusive), and none right after a switch
            fired, self.active = update_exclusive(self.tiles, dt if self.lock <= 0 else 0.0, pts, self.active)
            if fired is not None:
                self.cycle(fired, self.tiles[fired].c)
                self.lock = LOCK
                for other in self.tiles:
                    other.progress = 0.0
            if self.btn_photo.update(dt, pts):
                self.countdown = 3.0
                self.ctx.say("Drei, zwei, eins!")
                self._last_tick = 4
        else:
            self.countdown -= dt
            tick = math.ceil(self.countdown)
            if tick != self._last_tick and tick >= 1:
                self._last_tick = tick
                self.ctx.play("tick")
            if self.countdown <= 0:
                self.countdown = None
                self._shoot = True
        self.flash = max(0.0, self.flash - dt * 2.5)
        if self.thumb is not None:
            self.thumb_t += dt
            if self.thumb_t > 4.0:
                self.thumb = None
        # Zauberstab-Funken
        for p in (pose.all if pose and self._worn("hand") == "wand" else []):
            tip = self._hand_tip(p) if random.random() < 0.5 else None
            if tip:
                self.particles.burst(tip, 1, [(255, 235, 120), (255, 255, 255), (255, 170, 230)],
                                     90, 0.7, (3, 6), 60, "star")

    def _worn(self, key):
        """The piece currently chosen in a category (None = nothing)."""
        return self.order[key][self.sel[key]]

    def cycle(self, i, pos):
        key = SLOTS[i][0]
        self.sel[key] = (self.sel[key] + 1) % len(self.order[key])
        name = self._worn(key)
        self.ctx.play("poof")
        self.particles.burst(pos, 18, [(255, 255, 255), (255, 230, 120), (255, 160, 220)], 280, 0.7,
                             (3, 8), 200, "star")
        if name:
            self.ctx.say(C.NAMES[name])

    def _hand_geom(self, pose):
        for s in ("r", "l"):
            if pose.vis(f"{s}_wr") >= 0.4:
                wr = pose.P(f"{s}_wr")
                if pose.vis(f"{s}_el") >= 0.4:
                    d = wr - pose.P(f"{s}_el")
                else:
                    d = np.array([0.0, -1.0])
                n = float(np.hypot(*d)) or 1.0
                d = d / n
                d = d * 0.6 + np.array([0.0, -0.8])
                d = d / (float(np.hypot(*d)) or 1.0)
                return wr, d
        return None

    def _hand_tip(self, pose):
        g = self._hand_geom(pose)
        if not g:
            return None
        return (g[0][0] + g[1][0] * 0.95 * pose.torso(), g[0][1] + g[1][1] * 0.95 * pose.torso())

    # ---------------------------------------------------------- Zeichnen ---
    def _body_xf(self, pose, neck=False):
        """Shoulder line coordinates. Size from the shoulder width only: sitting close to the
        camera the hips are out of view or found in the wrong place (made everything too big).
        neck=True: origin moved up to the neck and a smaller unit, for bow tie, chain, tie..."""
        if not pose or not pose.has("l_sh", "r_sh"):
            return None
        l, r = pose.P("l_sh"), pose.P("r_sh")
        sw = float(np.hypot(*(r - l)))
        ang = math.atan2(r[1] - l[1], r[0] - l[0])
        sm = (l + r) / 2
        if neck:
            up = np.array([math.sin(ang), -math.cos(ang)]) * 0.14 * sw
            return Xf(sm[0] + up[0], sm[1] + up[1], 0.75 * sw, ang)
        return Xf(sm[0], sm[1], 1.4 * sw, ang)

    def draw_back(self, surf, pose):
        for p in (pose.all if pose else []):          # everybody in view gets dressed up
            xf = self._body_xf(p)
            if xf is None:
                continue
            alpha = None if self.ctx.has_mask else 150
            name = self._worn("back")
            if name:
                C.back_item(surf, xf, self.t, name, alpha)

    def play_draw(self, surf, pose):
        for p in (pose.all if pose else []):
            self._dress(surf, p)
        if self._shoot:
            self._shoot = False
            self._save_photo(surf)
        self._draw_ui(surf)

    def _dress(self, surf, pose):
        if pose.ok:
            head = pose.head()
            if head:
                eye_mid, hs, tilt = head
                s, c = math.sin(tilt), math.cos(tilt)
                hat = self._worn("hat")
                if hat:
                    org = eye_mid + np.array([s, -c]) * 0.5 * hs
                    C.HATS[hat](surf, Xf(org[0], org[1], hs * 1.15, tilt), self.t)
                gl = self._worn("glasses")
                if gl:
                    C.GLASSES[gl](surf, Xf(eye_mid[0], eye_mid[1], hs * 1.1, tilt), self.t)
                fc = self._worn("face")
                if fc:
                    n = pose.P("nose")
                    C.FACES[fc](surf, Xf(n[0], n[1], hs * 1.1, tilt), self.t)
            nk = self._worn("neck")
            xf = self._body_xf(pose, neck=True)
            if nk and xf:
                C.NECKS[nk](surf, xf, self.t)
            kind = self._worn("hand")
            if kind:
                g = self._hand_geom(pose)
                if g:
                    T = pose.torso()
                    bpos = None
                    if kind == "balloon":                   # every person has their own balloon
                        target = np.array([g[0][0], g[0][1] - 1.25 * T])
                        old = self.balloon.get(pose.slot)
                        b = self.balloon[pose.slot] = target if old is None else old + (target - old) * 0.12
                        bpos = tuple(b + np.array([math.sin(self.t * 1.7) * 0.06 * T, 0]))
                    C.hand_item(surf, kind, tuple(g[0]), tuple(g[1]), T, self.t, bpos)

    def _save_photo(self, surf):
        folder = os.path.join(self.ctx.out_dir, "fotos")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, time.strftime("camtoy_%Y%m%d_%H%M%S.png"))
        try:
            pygame.image.save(surf, path)
        except Exception as e:  # noqa: BLE001
            print("Foto konnte nicht gespeichert werden:", e)
        k = 240 / surf.get_width()
        self.thumb = pygame.transform.smoothscale(surf, (240, int(surf.get_height() * k)))
        self.thumb_t = 0.0
        self.flash = 1.0
        self.ctx.play("shutter")
        self.ctx.say("Tolles Foto!")
        self.particles.confetti(self.W, 50)

    def _draw_ui(self, surf):
        if self.countdown is None:
            for i, tile in enumerate(self.tiles):
                self._draw_tile(surf, i, tile)
            self.btn_photo.draw(surf, self.t)
        else:
            n = max(1, math.ceil(self.countdown))
            k = ease_out_back(1 - (self.countdown - (n - 1)))
            text(surf, str(n), int(260 * max(0.2, k)), (self.W // 2, self.H // 2), (255, 240, 120))
        if self.thumb is not None:
            k = min(1.0, self.thumb_t / 0.4)
            w, h = self.thumb.get_size()
            x = self.W - w - 30
            y = self.H - h - 30 + (1 - ease_out_back(k)) * 300
            frame = pygame.Rect(x - 10, y - 10, w + 20, h + 36)          # instant-photo look
            gfx.blit_center(surf, gfx.soft_shadow(frame.w, frame.h, 110), frame.move(4, 10).center)
            pygame.draw.rect(surf, (255, 255, 255), frame, border_radius=8)
            surf.blit(self.thumb, (x, y))
        if self.flash > 0:
            veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            veil.fill((255, 255, 255, int(255 * min(1, self.flash))))
            surf.blit(veil, (0, 0))

    def _draw_tile(self, surf, i, tile):
        key = SLOTS[i][0]
        name = self._worn(key)
        k = 1.0 + (0.08 if tile.hover else 0.0) + 0.06 * tile.progress
        if tile.hover:
            gfx.add_glow(surf, tile.c, tile.r * 1.9, (255, 210, 240), 0.55)
        gfx.blit_center(surf, button_sprite(tile.r, TILE_RIMS[i]), tile.c, scale=k)
        spr = gfx.cached(("dtile", key, name, tile.r),
                         lambda: gfx.icon_sprite(lambda s, c, r: _draw_item(s, key, name, c, r), tile.r,
                                                 pad=1.0, outline=3, shadow=0, depth=0.12))
        gfx.blit_center(surf, spr, tile.c, scale=k * 0.92)
        progress_ring(surf, tile.c, tile.r * k + 16, tile.progress)


TILE_RIMS = [(255, 200, 60), (90, 190, 255), (255, 120, 170), (120, 210, 120), (200, 90, 220), (255, 150, 70)]


def _draw_item(surf, key, name, c, r):
    """The costume piece a tile switches to, as a small picture (or a "+" for nothing yet)."""
    cx, cy = c
    if name is None:
        w = r * .16
        col = (130, 140, 190)
        pygame.draw.rect(surf, col, (cx - r * .38, cy - w, r * .76, 2 * w), border_radius=int(w))
        pygame.draw.rect(surf, col, (cx - w, cy - r * .38, 2 * w, r * .76), border_radius=int(w))
    elif key == "hat":
        C.HATS[name](surf, Xf(cx, cy + r * .4, r * 1.05), 0.0)
    elif key == "glasses":
        C.GLASSES[name](surf, Xf(cx, cy, r * 1.35), 0.0)
    elif key == "face":
        C.FACES[name](surf, Xf(cx, cy - r * .2, r * 1.5), 0.0)
    elif key == "back" and name in C.CAPES:
        C.cape(surf, Xf(cx, cy - r * .55, r * .58), 0.0, name)
    elif key == "back":
        C.back_item(surf, Xf(cx, cy + r * .25, r * .55), 0.0, name)
    elif key == "neck":                       # (vertical offset in r, size) so each piece fills the tile
        dy, k = {"bowtie": (0, 3.2), "pearls": (-.35, 2.6), "medal": (-.5, 1.75), "tie": (-.55, 1.7)}[name]
        C.NECKS[name](surf, Xf(cx, cy + dy * r, r * k), 0.0)
    elif key == "hand":
        if name == "balloon":
            C.hand_item(surf, name, (cx, cy + r * .6), (0, -1), r * .9, 0.0, (cx, cy - r * .2))
        elif name in ("wand", "sword"):
            C.hand_item(surf, name, (cx - r * .4, cy + r * .6), (.55, -.83), r * .85, 0.0)
        else:
            C.hand_item(surf, name, (cx - r * .3, cy + r * .55), (.5, -.86), r * 1.25, 0.0)
