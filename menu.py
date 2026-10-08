"""Mode menu (kids' look): big glossy buttons, a hand held on one for ~1 s starts that mode."""
import math

import numpy as np

import gfx
from minigames.common import (DwellButton, draw_button, draw_cursors, draw_hand, rainbow,
                              update_exclusive, veil)

TILE_COLORS = [(235, 95, 85), (70, 175, 255), (255, 130, 200), (95, 205, 110), (255, 160, 60),
               (240, 190, 70), (110, 150, 255)]


def draw_wave_hand(surf, c, t):
    """A waving hand invites to step in front of the camera and wave."""
    pulse = 0.5 + 0.5 * np.sin(t * 5)
    gfx.add_glow(surf, c, 110 + 14 * pulse, (255, 230, 140), 0.6)
    spr = gfx.cached(("wavehand",), lambda: gfx.icon_sprite(draw_hand, 70, pad=1.4, outline=4))
    gfx.blit_center(surf, spr, c, angle=float(np.sin(t * 6)) * 18)


class Menu:
    """entries: [(title, icon(surf, center, radius)), ...] - up to 7: two side columns, a 7th at the top centre."""

    def __init__(self, ctx, entries):
        self.ctx, self.W, self.H = ctx, ctx.W, ctx.H
        self.entries = entries
        self.t = 0.0
        # two columns at the sides: the middle stays free, because a standing player's
        # hands hang there and must not start a mode by accident
        ys = (0.24, 0.52, 0.80)
        spots = [(0.105 if i < 3 else 0.895, ys[i % 3]) for i in range(min(6, len(entries)))]
        spots += [(0.5, 0.33)] * (len(entries) - 6)      # a 7th entry sits at head height, top centre
        self.tiles = [DwellButton((fx * self.W, fy * self.H), 82, 1.1) for fx, fy in spots]

    def pause(self, seconds=1.5):
        """Back from a game: nothing starts for a moment, and a hand that is already on a
        button has to leave it first (no accidental next game)."""
        self.cooldown = seconds
        for tile in self.tiles:
            tile.progress, tile.armed = 0.0, False

    def update(self, dt, pose):
        self.t += dt
        # one point per hand - exactly the ball that is drawn - and only one tile fills at a time
        hands = pose.pointer_points() if pose else []
        if getattr(self, "cooldown", 0.0) > 0:
            self.cooldown -= dt
            for tile in self.tiles:
                tile.update(0.0, hands)                 # only tracks hover / re-arming
            return None
        fired, self.active = update_exclusive(self.tiles, dt, hands, getattr(self, "active", None))
        if fired is not None:
            self.ctx.play("click")
        return fired

    def draw(self, surf, pose):
        surf.blit(veil((self.W, self.H), (40, 50, 120, 50)), (0, 0))
        surf.blit(gfx.vignette((self.W, self.H)), (0, 0))
        title = "CamToy"
        f_w = 66
        x = self.W / 2 - len(title) * f_w / 2 + f_w / 2
        for i, ch in enumerate(title):
            bob = math.sin(self.t * 3 + i * 0.7)
            gfx.blit_center(surf, gfx.label(ch, 100, rainbow(i, 6, .62)), (x + i * f_w, 70 + 8 * bob),
                            angle=4 * math.sin(self.t * 2 + i))
        for i, ((name, icon), tile) in enumerate(zip(self.entries, self.tiles)):
            bob = (0, 4 * math.sin(self.t * 2.2 + i * 1.3))
            c = (tile.c[0], tile.c[1] + bob[1])
            draw_button(surf, c, tile.r, icon, (255, 255, 255), tile.hover, tile.progress, self.t,
                        base=TILE_COLORS[i])
        if not (pose and pose.ok):                    # nobody seen yet: a waving hand invites to wave
            draw_wave_hand(surf, (self.W / 2, self.H - 110), self.t)
        draw_cursors(surf, pose, self.t)
