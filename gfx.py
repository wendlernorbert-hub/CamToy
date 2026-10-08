"""Polished drawing: smooth (supersampled) sprites, puffy shading, sticker outlines, glow.

The look of the whole game comes from four steps, done once per sprite and then cached:
  1. draw the flat shape big (SS times the final size) with the plain pygame.draw calls,
  2. puff()    - light it like a soft rubber toy (rounded bevel, highlight),
  3. shrink    - smoothscale down, which gives clean anti-aliased edges,
  4. sticker() - a thick rounded outline and a soft drop shadow.
Per frame the game only blits (and sometimes scales) the cached sprites.
"""
import math
import os
import sys

import cv2
import numpy as np
import pygame

SS = 3                                   # supersampling factor
INK = (44, 34, 72)                       # outline colour used everywhere
_BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
FONT_FILE = os.path.join(_BASE, "assets", "fonts", "LilitaOne-Regular.ttf")

_cache = {}
_fleeting = {}                           # many short-lived variants (rotated particles): own budget


def cached(key, build, fleeting=False):
    store, limit = (_fleeting, 6000) if fleeting else (_cache, 6000)
    spr = store.get(key)
    if spr is None:
        if len(store) > limit:
            store.clear()
        spr = store[key] = build()
    return spr


# ------------------------------------------------------------------ fonts ---
_fonts = {}


def font(size):
    f = _fonts.get(size)
    if f is None:
        try:
            f = pygame.font.Font(FONT_FILE, size)
        except (FileNotFoundError, OSError):
            f = pygame.font.SysFont("arialrounded,segoeuiblack,arial", size, bold=True)
        _fonts[size] = f
    return f


def label(s, size, color=(255, 255, 255), outline=INK, width=None, shadow=True):
    """Game text: chunky rounded letters with an outline and a soft shadow."""
    width = max(2, size // 9) if width is None else width
    return cached(("label", s, size, tuple(color), tuple(outline), width, shadow),
                  lambda: sticker(font(size).render(s, True, color), width, outline,
                                  shadow=90 if shadow else 0, blur=max(2, size // 18)))


# --------------------------------------------------------------- building ---
def canvas(w, h):
    """Supersampled drawing surface for a sprite of final size (w, h)."""
    return pygame.Surface((int(w * SS), int(h * SS)), pygame.SRCALPHA)


def shrink(big, w, h):
    return pygame.transform.smoothscale(big, (max(1, int(w)), max(1, int(h))))


def icon_sprite(draw, r, pad=1.5, puffy=True, outline=4, depth=0.22, shadow=80):
    """Turns a draw(surface, center, radius) function into a polished sprite.
    r = radius of the drawing, pad = canvas half-size in radii (room for horns, tails, ...)."""
    half = r * pad
    ss = SS if r < 50 else 2                     # big sprites are smooth enough with 2x
    big = pygame.Surface((int(2 * half * ss), int(2 * half * ss)), pygame.SRCALPHA)
    c = big.get_width() / 2
    draw(big, (c, c), r * ss)
    if puffy:
        puff(big, depth * r * ss)
    spr = shrink(big, 2 * half, 2 * half)
    return sticker(spr, outline, INK, shadow=shadow) if outline else spr


def puff(surf, depth, light=(-0.5, -0.65), diffuse=0.55, spec=0.45, shine=24):
    """Shades a flat sprite in place so it looks soft and rounded (bevel from the silhouette)."""
    if depth < 1:
        return surf
    a = pygame.surfarray.pixels_alpha(surf)
    ys, xs = np.nonzero(a.T > 100)
    del a
    if len(xs) == 0:
        return surf
    p = 3                                        # only the painted part (canvases are mostly empty)
    x0, x1 = max(0, xs.min() - p), min(surf.get_width(), xs.max() + p + 1)
    y0, y1 = max(0, ys.min() - p), min(surf.get_height(), ys.max() + p + 1)
    sub = surf.subsurface((x0, y0, x1 - x0, y1 - y0))
    mask = (pygame.surfarray.array_alpha(sub).T > 100).astype(np.uint8)
    d = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    t = np.minimum(d * np.float32(1 / depth), 1)
    hgt = np.sqrt(1 - (1 - t) ** 2) * np.float32(depth)
    hgt = cv2.GaussianBlur(hgt, (0, 0), max(1.0, depth * 0.08))
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) * np.float32(1 / 8)
    gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) * np.float32(1 / 8)
    nz = 1.0 / np.sqrt(gx * gx + gy * gy + 1)
    lx, ly = light
    lz = math.sqrt(max(0.05, 1 - lx * lx - ly * ly))
    hx, hy, hz = lx, ly, lz + 1
    hn = math.sqrt(hx * hx + hy * hy + hz * hz)
    lam = np.clip((-gx * lx - gy * ly + lz) * nz, 0, 1)
    sp = cv2.pow(np.clip((-gx * hx - gy * hy + hz) * nz * np.float32(1 / hn), 0, 1), shine) * np.float32(spec)
    shade = 1.0 + diffuse * (lam - lz)          # the flat top keeps its own colour
    rgb = pygame.surfarray.pixels3d(sub)
    col = rgb.transpose(1, 0, 2).astype(np.float32)
    col = col * shade[..., None] + (255 * sp)[..., None]
    rgb[...] = np.clip(col, 0, 255).astype(np.uint8).transpose(1, 0, 2)
    del rgb
    return surf


def sticker(img, width=4, color=INK, shadow=80, offset=(0, 5), blur=5):
    """New sprite: img with a rounded outline and a soft drop shadow, same centre."""
    a = pygame.surfarray.array_alpha(img).T
    pad = width + 3 * blur + max(abs(offset[0]), abs(offset[1]))
    h, w = a.shape
    A = np.zeros((h + 2 * pad, w + 2 * pad), np.uint8)
    A[pad:pad + h, pad:pad + w] = a
    out = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
    if shadow:
        base = A if width <= 0 else _dilate(A, width)
        sh = cv2.GaussianBlur(base, (0, 0), blur).astype(np.float32) * (shadow / 255)
        M = np.float32([[1, 0, offset[0]], [0, 1, offset[1]]])
        sh = cv2.warpAffine(sh, M, (sh.shape[1], sh.shape[0]))
        out.blit(_solid(sh.astype(np.uint8), (20, 12, 40)), (0, 0))
    if width > 0:
        out.blit(_solid(_dilate(A, width), color), (0, 0))
    out.blit(img, (pad, pad))
    return out


def _dilate(a, width):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * width + 1, 2 * width + 1))
    return cv2.dilate(a, k)


def _solid(alpha_hw, color):
    s = pygame.Surface((alpha_hw.shape[1], alpha_hw.shape[0]), pygame.SRCALPHA)
    s.fill(tuple(color[:3]) + (255,))
    pygame.surfarray.pixels_alpha(s)[...] = alpha_hw.T
    return s


def ball(r, color, rim=None):
    """A shiny round disc (buttons, bubbles, eyes) - computed directly, perfectly smooth."""
    def build():
        n = int(2 * r + 4)
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
        u, v = (xx - n / 2 + 0.5) / r, (yy - n / 2 + 0.5) / r
        d = np.sqrt(u * u + v * v)
        alpha = np.clip((1 - d) * r + 0.5, 0, 1)
        z = np.sqrt(np.clip(1 - d * d, 0, 1))
        lam = np.clip(-0.45 * u - 0.6 * v + 0.66 * z, 0, 1)
        shade = 0.72 + 0.45 * lam
        spec = np.clip(1 - np.hypot(u + 0.38, v + 0.45) / 0.32, 0, 1) ** 1.6 * 0.75
        col = np.array(color[:3], np.float32)
        rgb = col * shade[..., None] + 255 * spec[..., None]
        if rim:                                         # coloured ring on the edge
            ring = np.clip((d - 0.86) * r / 2 + 0.5, 0, 1)[..., None]
            rgb = rgb * (1 - ring) + np.array(rim, np.float32) * ring
        s = pygame.Surface((n, n), pygame.SRCALPHA)
        pygame.surfarray.pixels3d(s)[...] = np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2)
        pygame.surfarray.pixels_alpha(s)[...] = (alpha * 255).astype(np.uint8).T
        return s
    return cached(("ball", int(r), tuple(color), rim), build)


def glow(r, color, power=1.0):
    """Soft light blob, drawn with BLEND_RGB_ADD (black = nothing)."""
    # sizes and strengths are rounded to a few steps: a glow that follows something moving
    # (shoulder width, a growing ring) must not be rebuilt every frame (play-test: 30 fps drops)
    r = int(r)
    step = 1 if r < 24 else (2 if r < 48 else (4 if r < 96 else 8))
    r = max(2, r // step * step)
    power = round(power * 20) / 20

    def build():
        n = int(2 * r)
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
        d = np.hypot(xx - n / 2 + 0.5, yy - n / 2 + 0.5) / r
        f = np.clip(1 - d, 0, 1) ** 2 * power
        rgb = np.array(color[:3], np.float32) * f[..., None]
        s = pygame.Surface((n, n))
        pygame.surfarray.pixels3d(s)[...] = np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2)
        return s
    return cached(("glow", r, tuple(color), power), build, fleeting=True)


def vignette(size, color=(20, 10, 50), strength=150):
    """Darker, coloured screen edges: makes the camera picture look framed and calm."""
    def build():
        w, h = size
        sw, sh = w // 4, h // 4
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        d = np.hypot((xx / sw - 0.5) * 2, (yy / sh - 0.5) * 2 * 0.85)
        a = np.clip((d - 0.75) / 0.6, 0, 1) ** 1.5 * strength
        s = _solid(a.astype(np.uint8), color)
        return pygame.transform.smoothscale(s, size)
    return cached(("vignette", tuple(size), tuple(color), strength), build)


def sunburst(r, color=(255, 235, 140), rays=14, alpha=70):
    def build():
        big = canvas(2 * r, 2 * r)
        c = r * SS
        for i in range(rays):
            a0 = 2 * math.pi * i / rays
            a1 = a0 + math.pi / rays
            pygame.draw.polygon(big, tuple(color) + (alpha,), [(c, c),
                                (c + math.cos(a0) * c * 1.5, c + math.sin(a0) * c * 1.5),
                                (c + math.cos(a1) * c * 1.5, c + math.sin(a1) * c * 1.5)])
        s = shrink(big, 2 * r, 2 * r)
        yy, xx = np.mgrid[0:2 * r, 0:2 * r].astype(np.float32)
        fade = np.clip(1 - np.hypot(xx - r, yy - r) / r, 0, 1) ** 0.7
        pa = pygame.surfarray.pixels_alpha(s)
        pa[...] = (pa * fade.T).astype(np.uint8)
        del pa
        return s
    return cached(("sunburst", r, tuple(color), rays, alpha), build)


def soft_shadow(w, h, alpha=90):
    """Blurred ellipse for objects standing / floating over the picture."""
    def build():
        pad = int(h * 0.6) + 4
        a = np.zeros((int(h) + 2 * pad, int(w) + 2 * pad), np.uint8)
        cv2.ellipse(a, (a.shape[1] // 2, a.shape[0] // 2), (int(w / 2), int(h / 2)), 0, 0, 360, alpha, -1)
        return _solid(cv2.GaussianBlur(a, (0, 0), max(1.0, h * 0.25)), (20, 12, 40))
    return cached(("shadow", int(w), int(h), alpha), build)


def white_copy(spr):
    """Same sprite as a white silhouette (hit flash)."""
    def build():
        s = spr.copy()
        s.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
        return s
    return cached(("white", id(spr)), build)


# ------------------------------------------------------------------ blits ---
def blit_center(dst, spr, pos, scale=1.0, angle=0.0, sx=1.0, sy=1.0):
    """Blit a sprite centred on pos, optionally scaled / squashed (sx, sy) / rotated (deg)."""
    if scale <= 0.01:
        return
    w, h = spr.get_size()
    if angle:
        spr = pygame.transform.rotozoom(spr, angle, scale)
        if sx != 1.0 or sy != 1.0:
            spr = pygame.transform.smoothscale(spr, (max(1, int(spr.get_width() * sx)),
                                                     max(1, int(spr.get_height() * sy))))
    elif scale != 1.0 or sx != 1.0 or sy != 1.0:
        spr = pygame.transform.smoothscale(spr, (max(1, int(w * scale * sx)), max(1, int(h * scale * sy))))
    dst.blit(spr, spr.get_rect(center=(int(pos[0]), int(pos[1]))))


def add_glow(dst, pos, r, color, power=1.0):
    if power < 0.025:
        return
    g = glow(max(2, int(r)), color, power)
    dst.blit(g, g.get_rect(center=(int(pos[0]), int(pos[1]))), special_flags=pygame.BLEND_RGB_ADD)


def aa_polygon(surf, color, pts, width=0):
    """Filled polygon with smoothed edges (anti-aliased outline drawn over it)."""
    pygame.draw.polygon(surf, color, pts, width)
    if width == 0 and len(pts) > 2:
        pygame.draw.aalines(surf, color, True, pts)


def lighter(c, k=0.35):
    return tuple(int(v + (255 - v) * k) for v in c[:3])


def darker(c, k=0.35):
    return tuple(int(v * (1 - k)) for v in c[:3])
