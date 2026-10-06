"""Shared look & feel: Ink-Wash / Sumi-e (rice paper, black ink, vermilion seals)."""
import math
import random

import pygame

DISPLAY_W = 1280
DISPLAY_H = 720

PAPER      = (238, 229, 208)
PAPER_DARK = (214, 199, 168)
INK        = (24, 22, 26)
INK_SOFT   = (74, 70, 76)
INK_WASH   = (132, 126, 124)
VERMILION  = (196, 46, 36)
VERMILION_DARK = (140, 30, 26)
GOLD       = (184, 146, 66)
MATCHA     = (74, 112, 82)       # "ok / go" tone that fits the ink palette

_FONT_DIR = "C:\\Windows\\Fonts\\"
_LATIN = ("Inkfree.ttf", "segoesc.ttf", "georgia.ttf")   # brush-like handwriting
_KANJI = ("YuGothB.ttc", "YuGothM.ttc", "msgothic.ttc", "simsun.ttc")

_font_cache: dict = {}


def _font(candidates, size: int) -> pygame.font.Font:
    key = (candidates, size)
    if key not in _font_cache:
        font = None
        for name in candidates:
            try:
                font = pygame.font.Font(_FONT_DIR + name, size)
                break
            except (FileNotFoundError, OSError, pygame.error):
                continue
        _font_cache[key] = font or pygame.font.SysFont("arial", size, bold=True)
    return _font_cache[key]


def latin(size: int) -> pygame.font.Font:
    return _font(_LATIN, size)


def kanji(size: int) -> pygame.font.Font:
    return _font(_KANJI, size)


def has_glyph(font: pygame.font.Font, ch: str) -> bool:
    try:
        return font.metrics(ch)[0] is not None
    except pygame.error:
        return False


def text_with_outline(font, text, color, outline=INK, width=2) -> pygame.Surface:
    """Render text with a hand-inked outline (alpha surface)."""
    base = font.render(text, True, color)
    edge = font.render(text, True, outline)
    w, h = base.get_size()
    out = pygame.Surface((w + width * 2 + 1, h + width * 2 + 1), pygame.SRCALPHA)
    # +1 px "faux bold": the brush-style fonts are too thin for a HUD
    for dx in range(-width, width + 2):
        for dy in range(-width, width + 2):
            if dx * dx + dy * dy <= (width + 1) ** 2:
                out.blit(edge, (width + dx, width + dy))
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        out.blit(base, (width + dx, width + dy))
    return out


def seal(glyph: str, size: int, angle: float = 0.0, color=VERMILION) -> pygame.Surface:
    """Red hanko stamp with a paper-coloured glyph, slightly irregular."""
    ss = size * 3
    surf = pygame.Surface((ss, ss), pygame.SRCALPHA)
    rnd = random.Random(hash(glyph) & 0xFFFF)
    pygame.draw.rect(surf, color, (ss * 0.04, ss * 0.04, ss * 0.92, ss * 0.92),
                     border_radius=int(ss * 0.12))
    # worn spots
    for _ in range(26):
        x, y = rnd.randint(0, ss), rnd.randint(0, ss)
        pygame.draw.circle(surf, (0, 0, 0, 0), (x, y), rnd.randint(1, 4))
    pygame.draw.rect(surf, PAPER, (ss * 0.12, ss * 0.12, ss * 0.76, ss * 0.76),
                     width=max(2, ss // 40), border_radius=int(ss * 0.07))
    f = kanji(int(ss * 0.56))
    g = f.render(glyph, True, PAPER)
    surf.blit(g, g.get_rect(center=(ss // 2, ss // 2 + ss * 0.02)))
    surf = pygame.transform.smoothscale(surf, (size, size))
    return pygame.transform.rotate(surf, angle) if angle else surf


def ink_blot(radius: int, seed: int, spikes: int = 14, color=INK) -> pygame.Surface:
    """Irregular ink splash with droplets, rendered once (alpha surface)."""
    rnd = random.Random(seed)
    ss = 3
    size = radius * 2 + 8
    surf = pygame.Surface((size * ss, size * ss), pygame.SRCALPHA)
    c = size * ss // 2
    pts = []
    n = spikes * 2
    for i in range(n):
        a = 2 * math.pi * i / n
        r = radius * ss * (rnd.uniform(0.95, 1.1) if i % 2 == 0 else rnd.uniform(0.45, 0.7))
        pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.circle(surf, color, (c, c), int(radius * ss * 0.55))
    for _ in range(spikes):
        a = rnd.uniform(0, 2 * math.pi)
        d = radius * ss * rnd.uniform(0.9, 1.45)
        pygame.draw.circle(surf, color, (c + math.cos(a) * d, c + math.sin(a) * d),
                           int(radius * ss * rnd.uniform(0.04, 0.12)))
    return pygame.transform.smoothscale(surf, (size, size))
