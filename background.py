import math
import random

import cv2
import numpy as np
import pygame

import theme
from theme import DISPLAY_W, DISPLAY_H, PAPER, INK, INK_SOFT, VERMILION

_HORIZON = 540
_SUN = (880, 205, 96)   # x, y, radius


def _noise(rnd: np.random.Generator, sigma: float) -> np.ndarray:
    """Zero-mean, unit-ish smooth noise (H, W)."""
    n = rnd.standard_normal((DISPLAY_H, DISPLAY_W)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), sigma)
    return n / (n.std() + 1e-6)


def _paper(rnd: np.random.Generator) -> np.ndarray:
    base = np.empty((DISPLAY_H, DISPLAY_W, 3), np.float32)
    base[:] = PAPER
    mottle = _noise(rnd, 60) * 5 + _noise(rnd, 14) * 2.5
    fibres = _noise(rnd, 0.8) * 2.2
    return base + (mottle + fibres)[..., None]


def _ridge(base: float, amp: float, seed: int) -> np.ndarray:
    rnd = random.Random(seed)
    x = np.arange(DISPLAY_W, dtype=np.float32)
    h = np.zeros(DISPLAY_W, np.float32)
    for freq, weight in ((1 / 260, 0.5), (1 / 120, 0.28), (1 / 47, 0.14), (1 / 19, 0.06)):
        h += weight * np.sin(x * freq * 2 * math.pi + rnd.uniform(0, 6.3))
    return base - amp * (0.55 + 0.45 * h)


def _wash_layer(bg, ridge, color, alpha, fade_len, grain) -> None:
    ys = np.arange(DISPLAY_H, dtype=np.float32)[:, None]
    inside = cv2.GaussianBlur((ys >= ridge[None, :]).astype(np.float32), (0, 0), 1.3)
    fade = np.clip(1 - (ys - ridge[None, :]) / fade_len, 0, 1) ** 1.4
    a = inside * alpha * (0.12 + 0.88 * fade) * (0.88 + 0.12 * grain)
    a = a[..., None]
    bg[:] = bg * (1 - a) + np.float32(color) * a


def _pagoda(layer, cx, base_y, scale, color) -> None:
    w = 120 * scale
    for i in range(4):
        rw = w * (1 - i * 0.18)
        y = base_y - i * 52 * scale
        body = pygame.Rect(0, 0, rw * 0.6, 34 * scale)
        body.midbottom = (cx, y)
        pygame.draw.rect(layer, color, body)
        roof = [(cx - rw * 0.75, y - 24 * scale), (cx - rw * 0.5, y - 32 * scale),
                (cx + rw * 0.5, y - 32 * scale), (cx + rw * 0.75, y - 24 * scale),
                (cx + rw * 0.4, y - 44 * scale), (cx - rw * 0.4, y - 44 * scale)]
        pygame.draw.polygon(layer, color, roof)
    top = base_y - 4 * 52 * scale
    pygame.draw.line(layer, color, (cx, top - 20 * scale), (cx, top - 62 * scale),
                     max(2, int(4 * scale)))


def _bamboo(layer, x, top, bottom, width, color, rnd: random.Random) -> None:
    y = bottom
    while y > top:
        seg = rnd.randint(70, 120)
        y2 = max(top, y - seg)
        pygame.draw.line(layer, color, (x, y), (x, y2), width)
        pygame.draw.line(layer, (*theme.PAPER, 150), (x - width // 2 + 1, y - 2),
                         (x - width // 2 + 1, y2 + 2), 1)
        # node
        pygame.draw.line(layer, color, (x - width, y2), (x + width, y2), max(2, width // 3))
        y = y2
        if rnd.random() < 0.55 and y2 > top + 40:
            d = rnd.choice((-1, 1))
            _leaves(layer, x, y2, d, color, rnd)


def _leaves(layer, x, y, d, color, rnd: random.Random) -> None:
    for _ in range(rnd.randint(3, 5)):
        a = math.radians(rnd.uniform(-35, 25)) + (0 if d > 0 else math.pi)
        ln = rnd.uniform(60, 110)
        ex, ey = x + math.cos(a) * ln, y + math.sin(a) * ln
        mx, my = (x + ex) / 2, (y + ey) / 2
        nx, ny = -math.sin(a) * 6, math.cos(a) * 6
        pygame.draw.polygon(layer, color, [(x, y), (mx + nx, my + ny), (ex, ey),
                                           (mx - nx, my - ny)])


def _blur_layer(layer: pygame.Surface, sigma: float) -> pygame.Surface:
    """Soften an alpha layer slightly so it reads as wet ink."""
    rgb = pygame.surfarray.array3d(layer).astype(np.float32)
    a = pygame.surfarray.array_alpha(layer).astype(np.float32)
    k = (0, 0)
    rgb = cv2.GaussianBlur(rgb, k, sigma)
    a = cv2.GaussianBlur(a, k, sigma)
    out = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(out)[:] = rgb.astype(np.uint8)
    pygame.surfarray.pixels_alpha(out)[:] = a.astype(np.uint8)
    return out


def _brush_strokes(bg, rnd: np.random.Generator) -> None:
    """Horizontal dry-brush streaks on the ground, like swept paper."""
    layer = np.zeros((DISPLAY_H, DISPLAY_W), np.float32)
    for _ in range(46):
        y = int(rnd.uniform(_HORIZON + 8, DISPLAY_H - 6))
        x = int(rnd.uniform(-100, DISPLAY_W - 150))
        ln = int(rnd.uniform(160, 520))
        th = max(1, int(1 + (y - _HORIZON) / 38 * rnd.uniform(0.4, 1.3)))
        cv2.line(layer, (x, y), (x + ln, y + int(rnd.uniform(-2, 2))),
                 float(rnd.uniform(0.15, 0.45)), th, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), 1.4)
    layer *= (0.6 + 0.4 * (_noise(rnd, 2.5) > -0.3))   # break up the strokes
    a = layer[..., None]
    bg[:] = bg * (1 - a) + np.float32(INK_SOFT) * a


def build_background() -> pygame.Surface:
    """Pre-render the static ink-wash scene once."""
    nprnd = np.random.default_rng(11)
    bg = _paper(nprnd)
    grain = _noise(nprnd, 3)

    # Sun: soft halo + hard vermilion disc
    sx, sy, sr = _SUN
    yy, xx = np.mgrid[0:DISPLAY_H, 0:DISPLAY_W].astype(np.float32)
    dist = np.hypot(xx - sx, yy - sy)
    halo = np.clip(1 - dist / (sr * 3.2), 0, 1) ** 2 * 0.22
    disc = np.clip((sr - dist) / 1.6 + 0.5, 0, 1) * 0.92 * (0.93 + 0.07 * grain)
    for a, col in ((halo, (222, 150, 110)), (disc, VERMILION)):
        a3 = a[..., None]
        bg = bg * (1 - a3) + np.float32(col) * a3

    # Mist-faded mountain ranges, far -> near
    wash = (96, 98, 108)
    _wash_layer(bg, _ridge(330, 150, 3), (150, 150, 158), 0.55, 230, grain)
    _wash_layer(bg, _ridge(410, 170, 5), wash, 0.62, 200, grain)
    _wash_layer(bg, _ridge(500, 150, 8), (58, 58, 68), 0.78, 170, grain)

    # Ground
    ys = np.arange(DISPLAY_H, dtype=np.float32)[:, None]
    ground = np.clip((ys - _HORIZON + 10) / 14, 0, 1)
    ground_tone = np.float32(theme.PAPER_DARK)
    a = (ground * 0.55)[..., None] * np.ones((1, DISPLAY_W, 1), np.float32)
    bg = bg * (1 - a) + ground_tone * a
    _brush_strokes(bg, nprnd)

    surf = pygame.surfarray.make_surface(np.clip(bg, 0, 255).astype(np.uint8).swapaxes(0, 1))

    # Silhouettes in wet ink
    ink = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
    _pagoda(ink, 250, 438, 1.0, (*INK, 200))
    rnd = random.Random(4)
    for x, top, w in ((38, 40, 11), (84, 150, 8), (1236, 20, 12), (1190, 130, 8), (1148, 250, 6)):
        _bamboo(ink, x, top, _HORIZON + 20, w, (*INK_SOFT, 235), rnd)
    surf.blit(_blur_layer(ink, 0.9), (0, 0))

    # Floor shadow where the player stands
    shadow = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (*INK, 90), (DISPLAY_W // 2 - 260, DISPLAY_H - 70, 520, 56))
    surf.blit(_blur_layer(shadow, 14), (0, 0))

    # Ink splatters for atmosphere
    for i, (x, y, r) in enumerate(((150, 600, 18), (1110, 640, 24), (700, 90, 10), (420, 110, 8))):
        blot = theme.ink_blot(r, 40 + i, 9, (*INK_SOFT,))
        blot.set_alpha(120)
        surf.blit(blot, blot.get_rect(center=(x, y)))

    # Paper vignette
    vig = np.clip(1 - 0.2 * ((xx / DISPLAY_W - 0.5) ** 2 + (yy / DISPLAY_H - 0.5) ** 2) * 4, 0.75, 1)
    arr = pygame.surfarray.pixels3d(surf)
    arr[:] = (arr.astype(np.float32) * vig.T[..., None]).astype(np.uint8)
    del arr

    # Scroll frame + artist's seal
    pygame.draw.rect(surf, INK, (10, 10, DISPLAY_W - 20, DISPLAY_H - 20), 3)
    pygame.draw.rect(surf, INK_SOFT, (18, 18, DISPLAY_W - 36, DISPLAY_H - 36), 1)
    stamp = theme.seal("拳", 54, -6)
    surf.blit(stamp, (DISPLAY_W - 96, DISPLAY_H - 96))
    return surf.convert()
