"""Kostüm-Teile, alle per Code gezeichnet (keine Bilddateien nötig).

Lokale Koordinaten: Einheit = Kopfbreite (Hut, Brille, Gesicht) bzw. Rumpflänge
(Umhang, Flügel). Xf rechnet in Bildschirm-Pixel um (Verschiebung, Skalierung, Drehung).
"""
import math

import pygame

from common import ellipse_pts, heart_pts, star_pts, poly_alpha


class Xf:
    def __init__(self, ox, oy, scale, angle=0.0):
        self.ox, self.oy, self.s = float(ox), float(oy), float(scale)
        self.c, self.sn = math.cos(float(angle)), math.sin(float(angle))

    def pt(self, x, y):
        x, y = x * self.s, y * self.s
        return (self.ox + x * self.c - y * self.sn, self.oy + x * self.sn + y * self.c)

    def pts(self, lst):
        return [self.pt(x, y) for x, y in lst]

    def ell(self, cx, cy, rx, ry, rot=0.0, n=22):
        return self.pts(ellipse_pts(cx, cy, rx, ry, rot, n))

    def r(self, v):
        return max(1, int(v * self.s))


def fill(surf, col, pts, edge=None, w=3):
    pygame.draw.polygon(surf, col, pts)
    if edge:
        pygame.draw.polygon(surf, edge, pts, w)


# ------------------------------------------------------------------ Hüte ---
# Ursprung: Mitte der Kopfoberseite, Hut wächst nach oben (negatives y).

def hat_crown(surf, xf, t):
    zig = [(-.5, .06), (-.5, -.42), (-.25, -.2), (0, -.52), (.25, -.2), (.5, -.42), (.5, .06)]
    fill(surf, (255, 205, 50), xf.pts(zig), (180, 120, 0))
    fill(surf, (215, 50, 80), xf.pts([(-.5, -.08), (.5, -.08), (.5, .06), (-.5, .06)]))
    for x, y, col in ((-.5, -.42, (230, 50, 60)), (0, -.52, (60, 120, 240)), (.5, -.42, (60, 200, 90))):
        p = xf.pt(x, y)
        pygame.draw.circle(surf, col, (int(p[0]), int(p[1])), xf.r(.07))
        pygame.draw.circle(surf, (255, 255, 255), (int(p[0] - 2), int(p[1] - 2)), max(1, xf.r(.02)))


def hat_wizard(surf, xf, t):
    fill(surf, (90, 55, 170), xf.pts([(-.46, 0), (.46, 0), (.10, -1.2)]), (50, 25, 110))
    fill(surf, (70, 40, 140), xf.ell(0, 0, .74, .13), (50, 25, 110))
    fill(surf, (255, 205, 60), xf.pts([(-.43, -.12), (.43, -.12), (.4, -.02), (-.4, -.02)]))
    for x, y, r in ((-.12, -.38, .08), (.12, -.62, .07), (0, -.9, .05)):
        fill(surf, (255, 235, 90), xf.pts(star_pts((x, y), r, math.sin(t * 2) * .3)))


def hat_top(surf, xf, t):
    fill(surf, (35, 35, 45), xf.ell(0, 0, .7, .11), (10, 10, 20))
    fill(surf, (35, 35, 45), xf.pts([(-.4, 0), (-.4, -.85), (.4, -.85), (.4, 0)]), (10, 10, 20))
    fill(surf, (60, 60, 75), xf.ell(0, -.85, .4, .07), (10, 10, 20))
    fill(surf, (210, 50, 70), xf.pts([(-.4, -.22), (.4, -.22), (.4, -.07), (-.4, -.07)]))


def hat_bunny(surf, xf, t):
    for side in (-1, 1):
        wob = math.sin(t * 3 + side) * 0.06
        fill(surf, (250, 250, 255), xf.ell(side * .24, -.55, .13, .5, side * .15 + wob), (160, 160, 180))
        fill(surf, (255, 170, 190), xf.ell(side * .24, -.55, .065, .38, side * .15 + wob))


# ---------------------------------------------------------------- Brillen ---
# Ursprung: Mitte zwischen den Augen.

def glasses_sun(surf, xf, t):
    for side in (-1, 1):
        fill(surf, (20, 20, 30), xf.ell(side * .23, 0, .2, .15), (0, 0, 0))
        fill(surf, (90, 100, 130), xf.ell(side * .23 - .06, -.05, .06, .03, -.4, 12))
        pygame.draw.line(surf, (20, 20, 30), xf.pt(side * .43, -.03), xf.pt(side * .62, 0.0), max(2, xf.r(.03)))
    pygame.draw.line(surf, (20, 20, 30), xf.pt(-.05, -.04), xf.pt(.05, -.04), max(2, xf.r(.03)))


def glasses_heart(surf, xf, t):
    for side in (-1, 1):
        pts = xf.pts(heart_pts((side * .24, -.01), .22))
        fill(surf, (255, 90, 150), pts, (190, 30, 90), 4)
        p = xf.pt(side * .24 - .07, -.07)
        pygame.draw.circle(surf, (255, 255, 255), (int(p[0]), int(p[1])), max(2, xf.r(.03)))
    pygame.draw.line(surf, (190, 30, 90), xf.pt(-.03, -.03), xf.pt(.03, -.03), max(2, xf.r(.03)))


def glasses_star(surf, xf, t):
    for side in (-1, 1):
        fill(surf, (255, 225, 60), xf.pts(star_pts((side * .24, 0), .24, math.sin(t * 2 + side) * .25, .5)),
             (230, 130, 0), 3)


# ---------------------------------------------------------------- Gesicht ---
# Ursprung: Nasenspitze.

def face_clown(surf, xf, t):
    p = xf.pt(0, 0)
    pygame.draw.circle(surf, (230, 40, 50), (int(p[0]), int(p[1])), xf.r(.17))
    pygame.draw.circle(surf, (255, 255, 255), (int(p[0] - xf.r(.06)), int(p[1] - xf.r(.06))), max(2, xf.r(.045)))


def face_mustache(surf, xf, t):
    for side in (-1, 1):
        fill(surf, (80, 45, 25), xf.ell(side * .15, .13, .19, .07, side * -.28), (40, 20, 10), 2)
    fill(surf, (80, 45, 25), xf.ell(0, .11, .06, .05))


def face_cat(surf, xf, t):
    fill(surf, (255, 130, 160), xf.pts([(-.08, -.04), (.08, -.04), (0, .06)]), (170, 60, 90), 2)
    for side in (-1, 1):
        for dy in (-.1, .02, .14):
            a, b = xf.pt(side * .1, .05), xf.pt(side * .58, .05 + dy)
            pygame.draw.line(surf, (40, 40, 50), a, b, max(3, xf.r(.03)) + 2)
            pygame.draw.line(surf, (255, 255, 255), a, b, max(1, xf.r(.03)))


# -------------------------------------------------------- Rücken (hinten) ---
# Ursprung: Schulter-Mitte, Einheit = Rumpflänge, x entlang der Schulterlinie.

CAPES = {"red": ((215, 40, 55), (150, 20, 35), (255, 215, 60)),
         "purple": ((120, 60, 190), (80, 35, 140), (250, 250, 250)),
         "green": ((50, 170, 90), (25, 120, 60), (255, 230, 120))}


def cape(surf, xf, t, variant, alpha=None):
    main, dark, collar = CAPES[variant]
    sway = math.sin(t * 2.6) * .07
    outline = [(-.52, -.04), (.52, -.04), (.62, .7), (.85 + sway, 1.65),
               (.45, 1.88), (0, 1.78 + sway * .5), (-.45, 1.88), (-.85 + sway, 1.65), (-.62, .7)]
    inner = [(-.38, .05), (.38, .05), (.46, .8), (.62 + sway, 1.5), (0, 1.55), (-.62 + sway, 1.5), (-.46, .8)]
    if alpha is None:
        fill(surf, main, xf.pts(outline), dark, 4)
        fill(surf, dark, xf.pts(inner))
    else:
        poly_alpha(surf, main + (alpha,), xf.pts(outline))
    pts = xf.ell(0, -.03, .55, .13)
    if alpha is None:
        fill(surf, collar, pts, (120, 90, 20), 2)
    else:
        poly_alpha(surf, collar + (alpha,), pts)


WINGS = {"fairy": ((150, 220, 255), (200, 240, 255), (60, 140, 200)),
         "butterfly": ((255, 150, 40), (255, 205, 80), (70, 40, 20)),
         "angel": ((255, 255, 255), (240, 245, 255), (150, 160, 190))}


def wings(surf, xf, t, variant, alpha=None):
    up, low, edge = WINGS[variant]
    flap = 0.88 + 0.12 * math.sin(t * 7)
    for side in (-1, 1):
        for (cx, cy, rx, ry, rot, col) in (
                (side * (.35 + .62 * flap), -.7, .78, .34, -side * .55, up),
                (side * (.3 + .42 * flap), .12, .5, .26, side * .45, low)):
            pts = xf.ell(cx, cy, rx * flap, ry, rot)
            if alpha is None:
                fill(surf, col, pts, edge, 4)
            else:
                poly_alpha(surf, col + (alpha,), pts)
        if variant == "butterfly" and alpha is None:
            for cx, cy, r in ((side * (.35 + .75 * flap), -.8, .09), (side * (.3 + .45 * flap), .14, .07)):
                p = xf.pt(cx, cy)
                pygame.draw.circle(surf, edge, (int(p[0]), int(p[1])), xf.r(r))


# ------------------------------------------------------------ Handobjekte ---

def hand_item(surf, kind, hand, direction, T, t, balloon_pos=None):
    """hand = Pixelposition, direction = Einheitsvektor, T = Rumpflänge in Pixel."""
    hx, hy = float(hand[0]), float(hand[1])
    dx, dy = float(direction[0]), float(direction[1])
    T = float(T)
    if balloon_pos is not None:
        balloon_pos = (float(balloon_pos[0]), float(balloon_pos[1]))
    if kind == "wand":
        L = 0.95 * T
        tip = (hx + dx * L, hy + dy * L)
        pygame.draw.line(surf, (60, 35, 20), (hx, hy), tip, 10)
        pygame.draw.line(surf, (150, 95, 50), (hx, hy), tip, 6)
        pts = star_pts(tip, T * 0.2, t * 2)
        fill(surf, (255, 230, 80), pts, (230, 140, 0), 3)
        return tip
    if kind == "sword":
        L = 1.15 * T
        nx, ny = -dy, dx
        base = (hx + dx * 0.15 * T, hy + dy * 0.15 * T)
        tip = (hx + dx * L, hy + dy * L)
        w = 0.07 * T
        blade = [(base[0] + nx * w, base[1] + ny * w), (base[0] - nx * w, base[1] - ny * w),
                 (tip[0] - nx * w * .4, tip[1] - ny * w * .4), (tip[0] + dx * w * 1.6, tip[1] + dy * w * 1.6),
                 (tip[0] + nx * w * .4, tip[1] + ny * w * .4)]
        fill(surf, (205, 212, 225), blade, (90, 100, 120), 3)
        pygame.draw.line(surf, (255, 255, 255), (base[0] + nx * w * .3, base[1] + ny * w * .3),
                         (tip[0] + nx * w * .1, tip[1] + ny * w * .1), 3)
        pygame.draw.line(surf, (230, 180, 40), (base[0] + nx * w * 2.2, base[1] + ny * w * 2.2),
                         (base[0] - nx * w * 2.2, base[1] - ny * w * 2.2), 10)
        pygame.draw.line(surf, (110, 60, 30), (hx, hy), base, 9)
        return tip
    if kind == "balloon":
        bx, by = balloon_pos if balloon_pos else (hx, hy - 1.2 * T)
        pygame.draw.line(surf, (240, 240, 240), (hx, hy), (bx, by + 0.4 * T), 3)
        fill(surf, (235, 60, 80), ellipse_pts(bx, by, 0.3 * T, 0.38 * T, 0, 28), (150, 20, 40), 3)
        fill(surf, (235, 60, 80), [(bx, by + .36 * T), (bx - .05 * T, by + .46 * T), (bx + .05 * T, by + .46 * T)])
        pygame.draw.ellipse(surf, (255, 190, 200), (bx - .17 * T, by - .27 * T, .11 * T, .17 * T))
        return (bx, by)
    return hand


HATS = {"crown": hat_crown, "wizard": hat_wizard, "top": hat_top, "bunny": hat_bunny}
GLASSES = {"sun": glasses_sun, "heart": glasses_heart, "star": glasses_star}
FACES = {"clown": face_clown, "mustache": face_mustache, "cat": face_cat}
NAMES = {"crown": "Krone", "wizard": "Zauberhut", "top": "Zylinder", "bunny": "Hasenohren",
         "sun": "Sonnenbrille", "heart": "Herzbrille", "star": "Sternbrille",
         "clown": "Clownsnase", "mustache": "Schnurrbart", "cat": "Katzennase",
         "red": "Superhelden-Umhang", "purple": "Königsumhang", "green": "Waldumhang",
         "fairy": "Feenflügel", "butterfly": "Schmetterlingsflügel", "angel": "Engelsflügel",
         "wand": "Zauberstab", "sword": "Schwert", "balloon": "Luftballon"}
