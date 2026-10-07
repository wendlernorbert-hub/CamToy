"""Mode menu (kids' look): big circles, a hand held on one for ~1 s starts that mode."""
import numpy as np
import pygame

from minigames.common import (DwellButton, circle_alpha, draw_cursors, draw_ring,
                              draw_stars_row, rainbow, text)

TILE_COLORS = [(235, 110, 90), (90, 190, 255), (255, 140, 205), (110, 215, 120), (255, 170, 70),
               (240, 190, 70), (110, 150, 255)]


def draw_wave_hand(surf, c, t):
    """Pictogram of a waving hand (no text: the players cannot read yet)."""
    pulse = 0.5 + 0.5 * np.sin(t * 5)
    circle_alpha(surf, (255, 240, 140, int(70 + 70 * pulse)), c, 78 + 8 * pulse)
    h = pygame.Surface((140, 160), pygame.SRCALPHA)
    skin, edge = (255, 214, 170), (60, 50, 80)
    for dx, top, hgt in ((-30, 22, 62), (-10, 6, 74), (10, 6, 74), (30, 22, 62)):     # fingers
        r = pygame.Rect(70 + dx - 10, top, 20, hgt)
        pygame.draw.ellipse(h, edge, r.inflate(4, 4))
        pygame.draw.ellipse(h, skin, r)
    th = pygame.Rect(0, 0, 20, 58)
    th.center = (30, 108)
    thumb = pygame.Surface((40, 70), pygame.SRCALPHA)
    pygame.draw.ellipse(thumb, edge, thumb.get_rect().inflate(-4, -4))
    pygame.draw.ellipse(thumb, skin, thumb.get_rect().inflate(-10, -10))
    thumb = pygame.transform.rotate(thumb, 40)
    h.blit(thumb, thumb.get_rect(center=(34, 108)))
    pygame.draw.ellipse(h, edge, (28, 62, 84, 86))
    pygame.draw.ellipse(h, skin, (32, 66, 76, 78))
    h = pygame.transform.rotate(h, float(np.sin(t * 6)) * 18)
    surf.blit(h, h.get_rect(center=(int(c[0]), int(c[1]))))


class Menu:
    """entries: [(title, icon(surf, center, radius)), ...] - up to 7: two side columns, a 7th at the top centre."""

    def __init__(self, ctx, entries):
        self.ctx, self.W, self.H = ctx, ctx.W, ctx.H
        self.entries = entries
        self.t = 0.0
        # two columns at the sides: the middle stays free, because a standing player's
        # hands hang there and must not start a mode by accident
        ys = (0.24, 0.50, 0.76)
        spots = [(0.115 if i < 3 else 0.885, ys[i % 3]) for i in range(min(6, len(entries)))]
        spots += [(0.5, 0.33)] * (len(entries) - 6)      # a 7th entry sits at head height, top centre
        self.tiles = [DwellButton((fx * self.W, fy * self.H), 80, 1.1) for fx, fy in spots]

    def update(self, dt, pose):
        self.t += dt
        hands = pose.hand_points() if pose else []
        for i, tile in enumerate(self.tiles):
            if tile.update(dt, hands):
                self.ctx.play("click")
                return i
        return None

    def draw(self, surf, pose):
        veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        veil.fill((30, 40, 100, 90))
        surf.blit(veil, (0, 0))
        title = "CamToy"
        f_w = 62
        x = self.W / 2 - len(title) * f_w / 2 + f_w / 2
        for i, ch in enumerate(title):
            text(surf, ch, 92, (x + i * f_w, 62 + 6 * np.sin(self.t * 3 + i)), rainbow(i, 6, .6))
        for i, ((name, icon), tile) in enumerate(zip(self.entries, self.tiles)):
            r = int(tile.r * (1.06 if tile.hover else 1.0) * (1 + 0.015 * np.sin(self.t * 2.5 + i)))
            circle_alpha(surf, TILE_COLORS[i] + (210,), tile.c, r)
            pygame.draw.circle(surf, (255, 255, 255), tile.c, r, 6)
            icon(surf, tile.c, int(r * 0.72))
            draw_ring(surf, tile.c, r + 14, r + 6, tile.progress, (255, 225, 60))
        draw_stars_row(surf, (self.W / 2, 140), 3, self.ctx.level, 26)   # difficulty (keys 1-3)
        if not (pose and pose.ok):                    # nobody seen yet: a waving hand invites to wave
            draw_wave_hand(surf, (self.W / 2, self.H - 90), self.t)
        draw_cursors(surf, pose, self.t)
