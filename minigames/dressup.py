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

from . import costumes as C
from .common import (DwellButton, Game, circle_alpha, ease_out_back, text)
from .costumes import Xf

SLOTS = [("hat", [None, "crown", "wizard", "top", "bunny"]),
         ("glasses", [None, "sun", "heart", "star"]),
         ("face", [None, "clown", "mustache", "cat"]),
         ("cape", [None, "red", "purple", "green"]),
         ("wings", [None, "fairy", "butterfly", "angel"]),
         ("hand", [None, "wand", "sword", "balloon"])]


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
        self.balloon = None
        self.ctx.tracker.set_segmentation(True)

    def on_exit(self):
        self.ctx.tracker.set_segmentation(False)

    # ---------------------------------------------------------- Logik ---
    def play_update(self, dt, pose, hands):
        if self.countdown is None:
            for i, tile in enumerate(self.tiles):
                if tile.update(dt, hands):
                    self.cycle(i, tile.c)
            if self.btn_photo.update(dt, hands):
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
        if pose and self.sel["hand"] == 1 and random.random() < 0.5:
            tip = self._hand_tip(pose)
            if tip:
                self.particles.burst(tip, 1, [(255, 235, 120), (255, 255, 255), (255, 170, 230)],
                                     90, 0.7, (3, 6), 60, "star")

    def cycle(self, i, pos):
        key, items = SLOTS[i]
        self.sel[key] = (self.sel[key] + 1) % len(items)
        name = items[self.sel[key]]
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
    def _body_xf(self, pose):
        if not pose or not pose.has("l_sh", "r_sh"):
            return None
        l, r = pose.P("l_sh"), pose.P("r_sh")
        sm = (l + r) / 2
        return Xf(sm[0], sm[1], pose.torso(), math.atan2(r[1] - l[1], r[0] - l[0]))

    def draw_back(self, surf, pose):
        xf = self._body_xf(pose)
        if xf is None:
            return
        alpha = None if self.ctx.has_mask else 150
        for key, fn, table in (("wings", C.wings, None), ("cape", C.cape, None)):
            idx = self.sel[key]
            if idx:
                variant = dict(SLOTS)[key][idx]
                fn(surf, xf, self.t, variant, alpha)

    def play_draw(self, surf, pose):
        if pose and pose.ok:
            head = pose.head()
            if head:
                eye_mid, hs, tilt = head
                s, c = math.sin(tilt), math.cos(tilt)
                hat = dict(SLOTS)["hat"][self.sel["hat"]]
                if hat:
                    org = eye_mid + np.array([s, -c]) * 0.5 * hs
                    C.HATS[hat](surf, Xf(org[0], org[1], hs * 1.15, tilt), self.t)
                gl = dict(SLOTS)["glasses"][self.sel["glasses"]]
                if gl:
                    C.GLASSES[gl](surf, Xf(eye_mid[0], eye_mid[1], hs * 1.1, tilt), self.t)
                fc = dict(SLOTS)["face"][self.sel["face"]]
                if fc:
                    n = pose.P("nose")
                    C.FACES[fc](surf, Xf(n[0], n[1], hs * 1.1, tilt), self.t)
            hi = self.sel["hand"]
            if hi:
                g = self._hand_geom(pose)
                if g:
                    kind = dict(SLOTS)["hand"][hi]
                    T = pose.torso()
                    bpos = None
                    if kind == "balloon":
                        target = np.array([g[0][0], g[0][1] - 1.25 * T])
                        self.balloon = target if self.balloon is None else self.balloon + (target - self.balloon) * 0.12
                        bpos = tuple(self.balloon + np.array([math.sin(self.t * 1.7) * 0.06 * T, 0]))
                    C.hand_item(surf, kind, tuple(g[0]), tuple(g[1]), T, self.t, bpos)
        if self._shoot:
            self._shoot = False
            self._save_photo(surf)
        self._draw_ui(surf)

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
            pygame.draw.rect(surf, (255, 255, 255), (x - 10, y - 10, w + 20, h + 36), border_radius=6)
            surf.blit(self.thumb, (x, y))
        if self.flash > 0:
            veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            veil.fill((255, 255, 255, int(255 * min(1, self.flash))))
            surf.blit(veil, (0, 0))

    def _draw_tile(self, surf, i, tile):
        key, items = SLOTS[i]
        cx, cy = tile.c
        r = tile.r
        circle_alpha(surf, (255, 255, 255, 190 if tile.hover else 130), tile.c, r)
        pygame.draw.circle(surf, (255, 255, 255), tile.c, r, 5)
        name = items[self.sel[key]]
        if name is None:
            pygame.draw.line(surf, (110, 120, 170), (cx - r * .3, cy), (cx + r * .3, cy), 7)
            pygame.draw.line(surf, (110, 120, 170), (cx, cy - r * .3), (cx, cy + r * .3), 7)
        elif key == "hat":
            C.HATS[name](surf, Xf(cx, cy + r * .4, r * 1.05), self.t)
        elif key == "glasses":
            C.GLASSES[name](surf, Xf(cx, cy, r * 1.35), self.t)
        elif key == "face":
            C.FACES[name](surf, Xf(cx, cy - r * .2, r * 1.5), self.t)
        elif key == "cape":
            C.cape(surf, Xf(cx, cy - r * .55, r * .58), self.t, name)
        elif key == "wings":
            C.wings(surf, Xf(cx, cy - r * .1, r * .5), self.t, name)
        elif key == "hand":
            if name == "balloon":
                C.hand_item(surf, name, (cx, cy + r * .6), (0, -1), r * .9, self.t, (cx, cy - r * .2))
            else:
                C.hand_item(surf, name, (cx - r * .4, cy + r * .6), (.55, -.83), r * .75, self.t)
        from .common import draw_ring
        draw_ring(surf, tile.c, r + 14, r + 5, tile.progress, (255, 225, 60))
