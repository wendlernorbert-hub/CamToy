"""Kostüm-Teile, alle per Code gezeichnet (keine Bilddateien nötig).

Lokale Koordinaten: Einheit = Kopfbreite (Hut, Brille, Gesicht) bzw. Rumpflänge
(Umhang, Flügel). Xf rechnet in Bildschirm-Pixel um (Verschiebung, Skalierung, Drehung).
"""
import math

import pygame

from .common import ellipse_pts, heart_pts, star_pts, poly_alpha


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


def hat_pirate(surf, xf, t):
    ink = (15, 15, 25)
    shape = [(-.66, .03), (-.55, -.36), (-.22, -.52), (0, -.44), (.22, -.52), (.55, -.36), (.66, .03), (0, -.08)]
    fill(surf, (35, 32, 40), xf.pts(shape), ink, 3)
    pygame.draw.lines(surf, (230, 180, 40), False, xf.pts([(-.6, -.04), (0, -.16), (.6, -.04)]), max(2, xf.r(.035)))
    for a in (.7, -.7):                                       # crossbones
        c, s = math.cos(a), math.sin(a)
        pygame.draw.line(surf, (245, 245, 245), xf.pt(-.12 * c, -.27 - .12 * s), xf.pt(.12 * c, -.27 + .12 * s),
                         max(2, xf.r(.04)))
    fill(surf, (245, 245, 245), xf.ell(0, -.31, .08, .075))
    for sx in (-.03, .03):
        p = xf.pt(sx, -.32)
        pygame.draw.circle(surf, ink, (int(p[0]), int(p[1])), max(1, xf.r(.018)))


def hat_cowboy(surf, xf, t):
    edge = (80, 45, 20)
    fill(surf, (170, 110, 55), xf.ell(0, -.02, .82, .14), edge, 3)
    fill(surf, (185, 122, 62), xf.pts([(-.36, -.04), (-.42, -.46), (-.14, -.54), (0, -.45), (.14, -.54),
                                       (.42, -.46), (.36, -.04)]), edge, 3)
    fill(surf, (90, 50, 25), xf.pts([(-.37, -.16), (.37, -.16), (.36, -.06), (-.36, -.06)]))
    fill(surf, (255, 215, 60), xf.pts(star_pts((0, -.11), .06, 0)))


def hat_party(surf, xf, t):
    cone = [(-.32, 0), (.32, 0), (0, -1.0)]
    fill(surf, (60, 170, 255), xf.pts(cone), (30, 90, 170), 3)
    for i, col in enumerate(((255, 90, 140), (255, 220, 60), (120, 220, 120))):
        y = -.18 - i * .26
        w = .32 * (1 + y)
        fill(surf, col, xf.pts([(-w, y), (w, y), (w * .82, y - .1), (-w * .82, y - .1)]))
    p = xf.pt(0, -1.02)
    pygame.draw.circle(surf, (255, 255, 255), (int(p[0]), int(p[1])), xf.r(.1))
    pygame.draw.circle(surf, (255, 120, 170), (int(p[0]), int(p[1])), xf.r(.1), max(1, xf.r(.02)))


def hat_chef(surf, xf, t):
    edge = (170, 175, 190)
    for x, y, r in ((-.27, -.52, .25), (.27, -.52, .25), (0, -.66, .3)):
        fill(surf, (252, 252, 255), xf.ell(x, y, r, r * .95), edge, 3)
    fill(surf, (250, 250, 255), xf.pts([(-.4, -.35), (.4, -.35), (.4, 0), (-.4, 0)]), edge, 3)
    pygame.draw.line(surf, edge, xf.pt(-.12, -.33), xf.pt(-.12, -.02), max(1, xf.r(.015)))
    pygame.draw.line(surf, edge, xf.pt(.12, -.33), xf.pt(.12, -.02), max(1, xf.r(.015)))


def hat_viking(surf, xf, t):
    for side in (-1, 1):                                       # horns
        fill(surf, (250, 240, 215), xf.pts([(side * .4, -.22), (side * .78, -.5), (side * .9, -.9),
                                           (side * .98, -.45), (side * .55, -.08)]), (150, 130, 100), 3)
    dome = [(x, y) for x, y in ellipse_pts(0, -.02, .56, .55, 0, 30) if y <= -.01]
    fill(surf, (150, 160, 180), xf.pts(sorted(dome, key=lambda p: math.atan2(p[1] + .02, p[0]))), (70, 75, 95), 3)
    fill(surf, (200, 165, 70), xf.pts([(-.58, -.12), (.58, -.12), (.58, .03), (-.58, .03)]), (120, 90, 30), 2)
    for x in (-.4, -.2, 0, .2, .4):
        p = xf.pt(x, -.045)
        pygame.draw.circle(surf, (250, 230, 150), (int(p[0]), int(p[1])), max(1, xf.r(.025)))


def hat_flowers(surf, xf, t):
    cols = [(255, 120, 170), (255, 220, 70), (150, 120, 255), (255, 150, 80), (120, 200, 255)]
    for i in range(7):
        u = -1 + 2 * i / 6
        x, y = u * .52, -.05 - .12 * (1 - u * u)
        for a in range(0, 360, 120):                           # leaves
            if i % 2:
                fill(surf, (80, 180, 90), xf.ell(x + .09 * math.cos(math.radians(a + 60)),
                                                   y + .09 * math.sin(math.radians(a + 60)), .06, .03, math.radians(a + 60), 10))
        col = cols[i % len(cols)]
        for k in range(5):
            a = k * 2 * math.pi / 5 + t * .5
            fill(surf, col, xf.ell(x + .065 * math.cos(a), y + .065 * math.sin(a), .055, .055, 0, 10))
        fill(surf, (255, 240, 120), xf.ell(x, y, .04, .04, 0, 10))


# ---------------------------------------------------------------- Brillen ---
# Ursprung: Mitte zwischen den Augen.

def glasses_round(surf, xf, t):
    for side in (-1, 1):
        poly_alpha(surf, (190, 225, 255, 70), xf.ell(side * .23, 0, .17, .17))
        pygame.draw.polygon(surf, (40, 35, 50), xf.ell(side * .23, 0, .17, .17), max(2, xf.r(.035)))
        pygame.draw.line(surf, (40, 35, 50), xf.pt(side * .4, -.02), xf.pt(side * .62, .0), max(2, xf.r(.03)))
    pygame.draw.lines(surf, (40, 35, 50), False, xf.pts([(-.07, -.02), (0, -.06), (.07, -.02)]), max(2, xf.r(.03)))


def glasses_goggles(surf, xf, t):
    strap = (255, 140, 40)
    pygame.draw.line(surf, strap, xf.pt(-.75, -.02), xf.pt(.75, -.02), max(3, xf.r(.07)))
    frame = [(-.52, -.17), (.52, -.17), (.55, .1), (.1, .2), (0, .12), (-.1, .2), (-.55, .1)]
    fill(surf, (30, 150, 220), xf.pts(frame), (20, 70, 120), 3)
    inner = [(-.45, -.11), (.45, -.11), (.47, .06), (.1, .14), (0, .07), (-.1, .14), (-.47, .06)]
    poly_alpha(surf, (210, 245, 255, 110), xf.pts(inner))
    pygame.draw.line(surf, (255, 255, 255), xf.pt(-.38, -.07), xf.pt(-.22, -.07), max(2, xf.r(.025)))


def glasses_mask(surf, xf, t):
    red, edge = (225, 40, 50), (120, 15, 25)
    for side in (-1, 1):                                       # eye rings (eyes stay visible)
        pygame.draw.polygon(surf, red, xf.ell(side * .23, -.01, .2, .15), max(4, xf.r(.08)))
        fill(surf, red, xf.pts([(side * .4, -.1), (side * .66, -.2), (side * .6, .04), (side * .41, .09)]), edge, 2)
    fill(surf, red, xf.pts([(-.08, -.08), (.08, -.08), (.06, .02), (-.06, .02)]))



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


def face_beard(surf, xf, t):
    brown, edge = (115, 70, 35), (60, 35, 15)
    beard = [(-.46, -.02), (-.43, .3), (-.27, .55), (0, .66), (.27, .55), (.43, .3), (.46, -.02),
             (.3, .14), (.16, .28), (0, .3), (-.16, .28), (-.3, .14)]
    fill(surf, brown, xf.pts(beard), edge, 3)
    face_mustache(surf, xf, t)


def face_pig(surf, xf, t):
    fill(surf, (255, 160, 180), xf.ell(0, .02, .16, .12), (200, 90, 120), 3)
    for side in (-1, 1):
        fill(surf, (170, 60, 90), xf.ell(side * .055, .02, .03, .05))


def face_dog(surf, xf, t):
    wag = math.sin(t * 6) * .02
    fill(surf, (255, 110, 140), xf.pts([(-.07, .22), (.07, .22), (.08 + wag, .4), (0, .46), (-.08 + wag, .4)]),
         (190, 50, 80), 2)
    fill(surf, (30, 25, 35), xf.ell(0, 0, .13, .09))
    fill(surf, (110, 110, 130), xf.ell(-.04, -.03, .04, .02))


def face_freckles(surf, xf, t):
    for side in (-1, 1):
        poly_alpha(surf, (255, 120, 140, 110), xf.ell(side * .3, .06, .11, .07))
        for dx, dy in ((-.06, -.02), (.02, -.04), (.06, .02), (-.02, .03), (.0, -.0)):
            p = xf.pt(side * (.2 + dx), -.05 + dy)
            pygame.draw.circle(surf, (170, 100, 60), (int(p[0]), int(p[1])), max(1, xf.r(.015)))


# ------------------------------------------------------------------ Hals ---
# Ursprung: Schulter-Mitte, Einheit = Rumpflänge (wie Umhang).

def neck_bowtie(surf, xf, t):
    for side in (-1, 1):
        fill(surf, (230, 40, 60), xf.pts([(0, -.02), (side * .17, -.1), (side * .17, .07)]), (130, 15, 30), 3)
        for dx, dy in ((.1, -.04), (.13, .03)):
            p = xf.pt(side * dx, dy)
            pygame.draw.circle(surf, (255, 255, 255), (int(p[0]), int(p[1])), max(1, xf.r(.015)))
    fill(surf, (190, 25, 45), xf.ell(0, -.015, .04, .05), (130, 15, 30), 2)


def neck_pearls(surf, xf, t):
    for i in range(13):
        u = -1 + 2 * i / 12
        p = xf.pt(u * .2, -.02 + .2 * (1 - u * u))
        r = max(2, xf.r(.03))
        pygame.draw.circle(surf, (190, 190, 205), (int(p[0]), int(p[1])), r + 1)
        pygame.draw.circle(surf, (250, 248, 255), (int(p[0]), int(p[1])), r)
        pygame.draw.circle(surf, (255, 255, 255), (int(p[0] - r * .3), int(p[1] - r * .3)), max(1, r // 3))


def neck_medal(surf, xf, t):
    for side, col in ((-1, (220, 40, 60)), (1, (40, 90, 220))):
        fill(surf, col, xf.pts([(side * .16, -.04), (side * .07, -.04), (0, .32), (side * .04, .34)]))
    fill(surf, (250, 200, 50), xf.ell(0, .42, .1, .1), (170, 120, 10), 3)
    fill(surf, (255, 235, 130), xf.pts(star_pts((0, .42), .06, math.sin(t * 2) * .2)))


def neck_tie(surf, xf, t):
    blue, dark = (50, 110, 220), (20, 50, 130)
    fill(surf, blue, xf.pts([(-.05, .04), (.05, .04), (.09, .55), (0, .66), (-.09, .55)]), dark, 3)
    fill(surf, blue, xf.pts([(-.06, -.04), (.06, -.04), (.05, .05), (-.05, .05)]), dark, 3)
    for y in (.15, .3, .45):
        pygame.draw.line(surf, (255, 220, 60), xf.pt(-.06, y), xf.pt(.06, y + .05), max(2, xf.r(.02)))


NECKS = {"bowtie": neck_bowtie, "pearls": neck_pearls, "medal": neck_medal, "tie": neck_tie}


# -------------------------------------------------------- Rücken (hinten) ---
# Ursprung: Schulter-Mitte, Einheit = Rumpflänge, x entlang der Schulterlinie.

CAPES = {"red": ((215, 40, 55), (150, 20, 35), (255, 215, 60)),
         "purple": ((120, 60, 190), (80, 35, 140), (250, 250, 250)),
         "green": ((50, 170, 90), (25, 120, 60), (255, 230, 120)),
         "blue": ((50, 110, 225), (30, 70, 165), (255, 255, 255))}


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


POINTY = {"bat": ((70, 45, 95), (110, 75, 140), (30, 15, 45)),
          "dragon": ((60, 160, 80), (130, 210, 110), (25, 80, 35))}


def pointy_wings(surf, xf, t, variant, alpha=None):
    """Bat / dragon wings: bony fingers with scalloped skin in between."""
    skin, light, edge = POINTY[variant]
    flap = 0.85 + 0.15 * math.sin(t * 6)
    for side in (-1, 1):
        root = (side * .18, -.25)
        tips = [(side * (.55 + .7 * flap), -1.05), (side * (.45 + .95 * flap), -.55),
                (side * (.4 + .8 * flap), -.05), (side * (.3 + .45 * flap), .35)]
        outline = [root] + [tips[0]]
        for a, b in zip(tips, tips[1:]):                     # scallops between the finger tips
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            outline += [(mx - side * .14, my), b]
        outline.append((side * .15, .2))
        pts = xf.pts(outline)
        if alpha is None:
            fill(surf, skin, pts, edge, 4)
            for tip in tips:
                pygame.draw.line(surf, light, xf.pt(*root), xf.pt(*tip), max(2, xf.r(.03)))
        else:
            poly_alpha(surf, skin + (alpha,), pts)


def back_item(surf, xf, t, name, alpha=None):
    """Everything on the back (capes and all kinds of wings) is one slot."""
    if name in CAPES:
        cape(surf, xf, t, name, alpha)
    elif name in WINGS:
        wings(surf, xf, t, name, alpha)
    elif name in POINTY:
        pointy_wings(surf, xf, t, name, alpha)


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
    nx, ny = -dy, dx
    if kind == "flower":
        L = 0.8 * T
        tip = (hx + dx * L, hy + dy * L)
        pygame.draw.line(surf, (40, 120, 50), (hx, hy), tip, max(4, int(T * .04)))
        mid = (hx + dx * L * .5, hy + dy * L * .5)
        fill(surf, (90, 190, 90), ellipse_pts(mid[0] + nx * T * .08, mid[1] + ny * T * .08, T * .1, T * .04,
                                              math.atan2(ny, nx), 14), (40, 120, 50), 2)
        for k in range(6):
            a = k * math.pi / 3 + t
            fill(surf, (255, 110, 160), ellipse_pts(tip[0] + math.cos(a) * T * .1, tip[1] + math.sin(a) * T * .1,
                                                    T * .08, T * .08, 0, 12), (200, 50, 100), 2)
        fill(surf, (255, 220, 60), ellipse_pts(tip[0], tip[1], T * .07, T * .07, 0, 14), (210, 150, 0), 2)
        return tip
    if kind == "icecream":
        L = 0.45 * T
        top = (hx + dx * L, hy + dy * L)
        w = T * .13
        fill(surf, (230, 170, 90), [(hx, hy), (top[0] + nx * w, top[1] + ny * w), (top[0] - nx * w, top[1] - ny * w)],
             (160, 100, 40), 3)
        for k, col in enumerate(((255, 180, 200), (130, 85, 55), (250, 245, 225))):
            c = (top[0] + dx * T * (.06 + .13 * k), top[1] + dy * T * (.06 + .13 * k))
            fill(surf, col, ellipse_pts(c[0], c[1], T * .15, T * .13, 0, 20), (120, 80, 70), 2)
        c = (top[0] + dx * T * .4, top[1] + dy * T * .4)
        pygame.draw.circle(surf, (220, 30, 50), (int(c[0]), int(c[1])), max(3, int(T * .045)))
        return c
    if kind == "lollipop":
        L = 0.75 * T
        tip = (hx + dx * L, hy + dy * L)
        pygame.draw.line(surf, (250, 250, 250), (hx, hy), tip, max(4, int(T * .035)))
        R = T * .22
        fill(surf, (255, 90, 150), ellipse_pts(tip[0], tip[1], R, R, 0, 28), (180, 40, 90), 3)
        swirl = [(tip[0] + math.cos(a + t * 2) * R * a / 12, tip[1] + math.sin(a + t * 2) * R * a / 12)
                 for a in [i * .3 for i in range(40)]]
        pygame.draw.lines(surf, (255, 255, 255), False, swirl, max(3, int(T * .03)))
        return tip
    return hand


HATS = {"crown": hat_crown, "wizard": hat_wizard, "top": hat_top, "bunny": hat_bunny, "pirate": hat_pirate,
        "cowboy": hat_cowboy, "party": hat_party, "chef": hat_chef, "viking": hat_viking, "flowers": hat_flowers}
GLASSES = {"sun": glasses_sun, "heart": glasses_heart, "star": glasses_star, "round": glasses_round,
           "goggles": glasses_goggles, "mask": glasses_mask}
FACES = {"clown": face_clown, "mustache": face_mustache, "cat": face_cat, "beard": face_beard,
         "pig": face_pig, "dog": face_dog, "freckles": face_freckles}
NAMES = {"crown": "Krone", "wizard": "Zauberhut", "top": "Zylinder", "bunny": "Hasenohren",
         "pirate": "Piratenhut", "cowboy": "Cowboyhut", "party": "Partyhut", "chef": "Kochmütze",
         "viking": "Wikingerhelm", "flowers": "Blumenkranz",
         "sun": "Sonnenbrille", "heart": "Herzbrille", "star": "Sternbrille", "round": "Runde Brille",
         "goggles": "Taucherbrille", "mask": "Heldenmaske",
         "clown": "Clownsnase", "mustache": "Schnurrbart", "cat": "Katzennase", "beard": "Bart",
         "pig": "Schweinenase", "dog": "Hundenase", "freckles": "Sommersprossen",
         "red": "Superhelden-Umhang", "purple": "Königsumhang", "green": "Waldumhang", "blue": "Blauer Umhang",
         "fairy": "Feenflügel", "butterfly": "Schmetterlingsflügel", "angel": "Engelsflügel",
         "bat": "Fledermausflügel", "dragon": "Drachenflügel",
         "wand": "Zauberstab", "sword": "Schwert", "balloon": "Luftballon", "flower": "Blume",
         "icecream": "Eis", "lollipop": "Lolli",
         "bowtie": "Fliege", "pearls": "Perlenkette", "medal": "Medaille", "tie": "Krawatte"}
