"""Spiel 6: Pizza backen - Zutaten holen und vorbereiten, belegen, im Steinofen backen, aufessen.

Ablauf (kein Verlieren, alles mit den Händen). Der Teig ist zuerst ganz ohne Soße.
  1. Ganze Zutat (Tomate, Paprika, Oliven, Pilz, Salami, Käse) am Rand: Hand drauf halten.
  2. Vorbereiten, je nach Zutat: Tomaten püriert der Pürierstab von selbst zu Soße, Käse an der
     Reibe reiben (Hand auf und ab), Salami und Pilze mit dem Messer in Scheiben. Das Messer wartet
     schon über der Zutat; die Hand nimmt es, und es schneidet, wenn man es dort hält (oder schnell
     nach unten hackt). Die Hand, die an das Brett kommt, hat Messer bzw. Käse von selbst in der Hand.
  3. Belegen: Soße mit der Kelle über die Pizza streichen, Käse darüber streuen (die Hand
     bewegt sich über der Pizza), Stücke einzeln hintragen und mit stiller Hand ablegen.
  4. Ofen-Knopf oben rechts (wie "nochmal") -> ein Steinofen kommt, die Pizza hineinschieben,
     7 Sekunden backen (sie wird goldbraun), in 8 Stücke schneiden, der Koch probiert ein Stück -
     genau das geschnittene Stück dieser Pizza, Biss für Biss.
Passiert ein paar Sekunden nichts, macht eine durchsichtige Hand den nächsten Schritt vor.
Belohnung ist der glückliche Koch; die Wertung (Menge, Vielfalt, Soße) steht nur im Log.
"""
import math
import random
from collections import deque

import numpy as np
import pygame

import gfx
from .common import (DwellButton, Game, button_sprite, circle_alpha, ease_out_back, ease_out_cubic,
                     ellipse_pts, ghost_hand, heart_pts, progress_ring, star_pts)

R = 170                       # Pizza-Radius
MAX_TOPPINGS = 60             # pieces (salami, mushrooms)
MAX_CHEESE = 260              # grated cheese bits
PICK_TIME = 0.6               # Hand so lange auf der ganzen Zutat halten
PIECES = 8                    # Stücke pro geschnittener Zutat
CHOP_SPEED = {1: 220, 2: 340, 3: 460}     # px/s nach unten = ein Hackschlag
CHOP_GAP = 0.28               # Sekunden zwischen zwei Schnitten
HOVER_CUT = {1: 0.85, 2: 1.0, 3: 1.2}     # oder: so lange das Messer über der Zutat halten = ein Schnitt
CUT_REACH = 95                # px um die Schnittstelle, in denen das Halten schneidet
TAKE_REACH = 120              # px um das wartende Messer, in denen die Hand es nimmt
CUT_FRAC = 0.17               # jeder Schnitt nimmt so viel von der sichtbaren Länge der Zutat
PLACE_TIME = 0.4              # Hand mit Stück so lange still über der Pizza = ablegen
STILL_SPEED = 160             # px/s: langsamer zählt als "still"
BAKE_TIME = 7.0
# how each ingredient is made ready: knife on the board, hand blender for the tomatoes
# (they become sauce), the grater for the cheese - and how many strokes that takes
TOOL = {"tomato": "blender", "cheese": "grater"}      # everything else: "knife"
WORK = {"knife": 4, "blender": 6, "grater": 6}        # blender: steps of its own little show
BLEND_TIME = 1.6              # seconds the blender whirs by itself until the sauce is ready
SAUCE_DABS = 400              # a pot of mashed tomatoes is enough to cover the whole pizza
CHEESE_HANDFULS = 120         # the same for a bowl of grated cheese
DAB_R = 34                    # radius of one smear of sauce
SLICE_CUT = 0.5               # seconds the pizza cutter needs for one cut (4 cuts = 8 slices)
# eating (seconds into the "eat" phase): customer rises, takes a slice, 3 bites, "mmmh!", done
EAT_TAKE, EAT_BITES, EAT_YUM, EAT_END = 1.0, (1.05, 1.6, 2.15), 2.7, 4.2
SLICE_LIFT = 0.45             # seconds the real slice flies from the pizza to the chef's mouth
SLICE_HANG = -157.5           # degrees: the slice turns so its tip points up into the mouth
SLICE_HOLD = 0.6              # its size at the mouth
BITE = 0.28                   # one bite takes this much of the slice's length (times R)
PUSH_SPEED = 2.5              # so schnell (Anteil des Wegs pro Sekunde) folgt die Pizza der schiebenden Hand
HINT_AFTER = 4.0              # so lange nichts passiert: eine Geister-Hand zeigt, was als Nächstes dran ist

KINDS = ["tomato", "cheese", "salami", "mushroom"]       # (pepper and olive are drawn too, for later)
NAMES = {"tomato": "Tomate", "pepper": "Paprika", "olive": "Oliven", "mushroom": "Pilze",
         "salami": "Salami", "cheese": "Käse"}
S = 64                        # Größe eines Stücks in Pixeln


# ----------------------------------------------------------- ganze Zutaten ---

def _whole(surf, kind, c, r):
    """The whole ingredient as you would buy it, so children recognise it."""
    x, y = c
    if kind == "tomato":
        pygame.draw.circle(surf, (225, 45, 40), (int(x), int(y + r * .08)), int(r * .82))
        pygame.draw.ellipse(surf, (250, 120, 100), (x - r * .5, y - r * .45, r * .35, r * .22))
        pygame.draw.polygon(surf, (60, 150, 50), star_pts((x, y - r * .62), r * .36, 0.3, .35, 5))
        pygame.draw.line(surf, (60, 120, 40), (x, y - r * .65), (x + r * .08, y - r * .95), max(3, int(r * .1)))
    elif kind == "pepper":
        green, dark = (70, 170, 55), (40, 110, 35)
        for dx, w in ((-.36, .5), (.36, .5), (0, .56)):          # three lobes
            pygame.draw.ellipse(surf, green if dx else (90, 190, 70),
                                (x + (dx - w / 2) * r, y - r * .55, w * r, r * 1.4))
        pygame.draw.line(surf, dark, (x - r * .1, y - r * .4), (x - r * .1, y + r * .7), max(2, int(r * .04)))
        pygame.draw.line(surf, dark, (x + r * .14, y - r * .4), (x + r * .14, y + r * .7), max(2, int(r * .04)))
        pygame.draw.ellipse(surf, (150, 225, 120), (x - r * .55, y - r * .3, r * .16, r * .55))
        pygame.draw.rect(surf, (90, 130, 50), (x - r * .08, y - r * .85, r * .16, r * .36), border_radius=int(r * .06))
    elif kind == "olive":
        for dx, dy, a in ((-.38, .2, -.4), (.36, .25, .3), (0, -.25, .0)):
            pts = ellipse_pts(x + dx * r, y + dy * r, r * .34, r * .44, a, 24)
            pygame.draw.polygon(surf, (40, 40, 50), pts)
            pygame.draw.ellipse(surf, (110, 115, 140), (x + (dx - .15) * r, y + (dy - .28) * r, r * .12, r * .18))
        pygame.draw.lines(surf, (90, 130, 60), False, [(x - r * .7, y - r * .7), (x - r * .1, y - r * .6),
                                                         (x + r * .5, y - r * .2)], max(2, int(r * .06)))
    elif kind == "mushroom":
        pygame.draw.rect(surf, (245, 235, 215), (x - r * .24, y - r * .05, r * .48, r * .82), border_radius=int(r * .16))
        cap = pygame.Rect(0, 0, r * 1.7, r * 1.05)
        cap.midbottom = (int(x), int(y + r * .15))
        pygame.draw.ellipse(surf, (190, 130, 80), cap)
        pygame.draw.ellipse(surf, (220, 165, 110), cap.inflate(-r * .3, -r * .35).move(0, -r * .08))
        for dx, dy, rr in ((-.4, -.45, .1), (.25, -.55, .08), (.45, -.3, .07)):
            pygame.draw.circle(surf, (245, 225, 190), (int(x + dx * r), int(y + dy * r)), int(rr * r))
    elif kind == "salami":
        log = [(x - r * .85, y + r * .1), (x + r * .55, y - r * .35), (x + r * .7, y + r * .05), (x - r * .7, y + r * .5)]
        pygame.draw.polygon(surf, (140, 40, 40), log)
        pygame.draw.circle(surf, (140, 40, 40), (int(x - r * .78), int(y + r * .3)), int(r * .22))
        end = ellipse_pts(x + r * .63, y - r * .15, r * .24, r * .22, .3, 22)       # cut end shows the inside
        pygame.draw.polygon(surf, (205, 75, 65), end)
        for dx, dy in ((.58, -.2), (.7, -.1), (.62, -.05)):
            pygame.draw.circle(surf, (245, 160, 145), (int(x + dx * r), int(y + dy * r)), max(2, int(r * .045)))
        for dx, dy in ((-.4, .15), (-.1, .05), (.2, -.08), (-.25, .35), (.1, .2)):
            pygame.draw.circle(surf, (230, 200, 190), (int(x + dx * r), int(y + dy * r)), max(2, int(r * .04)))
        pygame.draw.line(surf, (240, 230, 210), (x - r * .9, y + r * .15), (x - r * 1.05, y - r * .05), max(2, int(r * .05)))
    else:                                                          # cheese wedge with holes
        top = [(x - r * .85, y - r * .05), (x + r * .55, y - r * .55), (x + r * .85, y - r * .2)]
        front = [(x - r * .85, y - r * .05), (x + r * .85, y - r * .2), (x + r * .85, y + r * .45), (x - r * .85, y + r * .6)]
        pygame.draw.polygon(surf, (250, 200, 50), front)
        pygame.draw.polygon(surf, (255, 230, 110), top)
        for dx, dy, rr in ((-.4, .25, .13), (.2, .3, .1), (.55, .1, .08), (.1, -.3, .07)):
            pygame.draw.circle(surf, (215, 160, 30), (int(x + dx * r), int(y + dy * r)), int(rr * r))


def whole_sprite(kind, r=58):
    return gfx.cached(("whole", kind, r), lambda: gfx.icon_sprite(lambda s, c, rr: _whole(s, kind, c, rr), r,
                                                                 pad=1.25, outline=4, depth=0.2))


# ----------------------------------------------------------------- Stücke ---

def make_topping(kind, size=S):
    """One cut piece (alpha surface size x size), supersampled."""
    k = 2
    z = size * k
    s = pygame.Surface((z, z), pygame.SRCALPHA)
    c = z // 2
    if kind == "salami":
        pygame.draw.circle(s, (120, 35, 35), (c, c), int(z * 0.47))
        pygame.draw.circle(s, (200, 70, 62), (c, c), int(z * 0.43))
        for dx, dy in ((-.18, -.12), (.14, -.2), (.2, .12), (-.08, .2), (0, 0)):
            pygame.draw.circle(s, (238, 140, 125), (int(c + dx * z), int(c + dy * z)), int(z * 0.05))
    elif kind == "mushroom":
        stem = pygame.Rect(0, 0, int(z * 0.26), int(z * 0.34))
        stem.midtop = (c, int(c + z * 0.02))
        pygame.draw.rect(s, (248, 238, 218), stem, border_radius=int(z * 0.07))
        cap = pygame.Rect(0, 0, int(z * 0.86), int(z * 0.6))
        cap.midbottom = (c, int(c + z * 0.1))
        pygame.draw.ellipse(s, (190, 140, 95), cap)
        pygame.draw.ellipse(s, (240, 215, 180), cap.inflate(-max(4, z // 10), -max(4, z // 10)))
    elif kind == "pepper":                                    # green pepper ring
        pygame.draw.circle(s, (45, 120, 40), (c, c), int(z * 0.46))
        pygame.draw.circle(s, (95, 190, 70), (c, c), int(z * 0.42))
        pygame.draw.circle(s, (0, 0, 0, 0), (c, c), int(z * 0.27))
        pygame.draw.circle(s, (45, 120, 40), (c, c), int(z * 0.28), max(2, k * 2))
    elif kind == "olive":                                     # olive ring
        pygame.draw.circle(s, (20, 20, 28), (c, c), int(z * 0.3))
        pygame.draw.circle(s, (55, 56, 70), (c, c), int(z * 0.26))
        pygame.draw.circle(s, (0, 0, 0, 0), (c, c), int(z * 0.11))
        pygame.draw.circle(s, (130, 135, 160), (int(c - z * .1), int(c - z * .12)), int(z * 0.04))
    elif kind == "tomato":                                    # tomato slice with seeds
        pygame.draw.circle(s, (200, 35, 35), (c, c), int(z * 0.46))
        pygame.draw.circle(s, (240, 80, 70), (c, c), int(z * 0.4))
        for i in range(5):
            a = i * 2 * math.pi / 5
            pygame.draw.circle(s, (255, 160, 130), (int(c + math.cos(a) * z * .2), int(c + math.sin(a) * z * .2)),
                               int(z * 0.1))
            pygame.draw.circle(s, (250, 230, 170), (int(c + math.cos(a) * z * .2), int(c + math.sin(a) * z * .2)),
                               int(z * 0.035))
        pygame.draw.circle(s, (230, 70, 60), (c, c), int(z * 0.08))
    else:                                                     # cheese: a few fine grated shreds
        for dx, dy, a in ((-.2, -.15, 20), (.15, -.2, -35), (-.05, .08, 65), (.22, .15, -10), (-.22, .22, -55)):
            x0, y0 = c + dx * z, c + dy * z
            ln = z * .16
            ang = math.radians(a)
            p0 = (x0 - math.cos(ang) * ln, y0 - math.sin(ang) * ln)
            p1 = (x0 + math.cos(ang) * ln, y0 + math.sin(ang) * ln)
            pygame.draw.line(s, (225, 175, 50), p0, p1, max(4, z // 11))
            pygame.draw.line(s, (255, 232, 120), p0, p1, max(2, z // 20))
    return pygame.transform.smoothscale(s, (size, size))


def topping_sprite(kind, size=S):
    """Polished piece: rounded shading, thin outline and a small shadow."""
    return gfx.cached(("topping", kind, size), lambda: gfx.sticker(
        gfx.puff(make_topping(kind, size), size * 0.12), 2, gfx.darker((90, 50, 30), 0.2),
        shadow=70, offset=(0, 3), blur=2))


# ---------------------------------------------------------- Pizza & Küche ---
_pizza_cache = {}


def pizza_base():
    """Wooden board and plain dough (made once) - the sauce is put on by the player."""
    if "base" not in _pizza_cache:
        z = (R + 60) * 2
        board = pygame.Surface((z, z), pygame.SRCALPHA)
        c = z // 2
        pygame.draw.circle(board, (150, 98, 55), (c, c), R + 36)
        pygame.draw.circle(board, (176, 120, 70), (c, c), R + 22, 3)
        gfx.puff(board, 14)
        s = pygame.Surface((z, z), pygame.SRCALPHA)
        pygame.draw.circle(s, (232, 182, 100), (c, c), R - 2)
        rnd = random.Random(4)
        for _ in range(26):                       # Teigblasen am Rand
            a = rnd.uniform(0, 2 * math.pi)
            rr = R - 14
            pygame.draw.circle(s, (246, 208, 132), (int(c + math.cos(a) * rr), int(c + math.sin(a) * rr)),
                               rnd.randint(4, 8))
        pygame.draw.circle(s, (240, 205, 140), (c, c), R - 28)                  # flat dough
        for _ in range(30):                       # flour dust
            a, d = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, R - 40)
            pygame.draw.circle(s, (248, 222, 170), (int(c + math.cos(a) * d), int(c + math.sin(a) * d)),
                               rnd.randint(2, 5))
        gfx.puff(s, 30)                            # a round, puffy crust
        pie = gfx.sticker(s, 0, shadow=90, offset=(0, 6), blur=6)
        board.blit(pie, pie.get_rect(center=(c, c)))
        _pizza_cache["base"] = gfx.sticker(board, 3, (90, 55, 30), shadow=110, offset=(0, 10), blur=10)
    return _pizza_cache["base"]


def _board(surf, c, r):
    x, y = c
    pygame.draw.rect(surf, (190, 140, 85), (x - r * 1.5, y - r * .7, r * 3.0, r * 1.4), border_radius=int(r * .3))
    pygame.draw.circle(surf, (190, 140, 85), (int(x + r * 1.6), int(y)), int(r * .28))
    pygame.draw.circle(surf, (0, 0, 0, 0), (int(x + r * 1.66), int(y)), int(r * .1))
    for k in (-.35, 0, .35):
        pygame.draw.line(surf, (170, 120, 70), (x - r * 1.3, y + k * r), (x + r * 1.3, y + k * r + 4), max(2, int(r * .03)))


def board_sprite():
    return gfx.cached(("cutboard",), lambda: gfx.icon_sprite(_board, 80, pad=2.0, outline=4, depth=0.08))


def _bowl(surf, c, r):
    x, y = c
    pygame.draw.ellipse(surf, (120, 170, 230), (x - r, y - r * .3, 2 * r, r * 1.25))
    pygame.draw.ellipse(surf, (80, 125, 190), (x - r * .92, y - r * .32, r * 1.84, r * .5))


def bowl_sprite():
    return gfx.cached(("bowl",), lambda: gfx.icon_sprite(_bowl, 78, pad=1.15, outline=4, depth=0.2))


def _oven(surf, c, r, hole=False):
    """Stone oven: domed brick body, dark arched mouth, chimney.
    hole=True: the mouth is cut out (the front layer, drawn over the pizza inside)."""
    x, y = c
    pygame.draw.rect(surf, (150, 85, 60), (x - r * 1.05, y + r * .35, r * 2.1, r * .6), border_radius=int(r * .08))
    pygame.draw.rect(surf, (120, 70, 55), (x + r * .55, y - r * 1.35, r * .3, r * .7))
    dome = ellipse_pts(x, y + r * .35, r * 1.0, r * 1.1, 0, 40)
    pygame.draw.polygon(surf, (185, 175, 165), [p for p in dome if p[1] <= y + r * .36])
    rnd = random.Random(7)
    for row in range(5):                                       # stones
        yy = y + r * .3 - row * r * .22
        half = math.sqrt(max(0.0, 1 - ((yy - y - r * .35) / (r * 1.1)) ** 2)) * r * .95
        n = max(2, int(half / (r * .2)))
        for i in range(n):
            xx = x - half + (i + .5 + (row % 2) * .5) * (2 * half / (n + .5))
            pygame.draw.ellipse(surf, rnd.choice([(160, 150, 140), (200, 190, 180), (170, 160, 150)]),
                                (xx - r * .1, yy - r * .08, r * .2, r * .15))
    mouth = [(x - r * .55, y + r * .36)] + [(x + math.cos(a) * r * .55, y + r * .36 - math.sin(a) * r * .55)
                                           for a in [i * math.pi / 20 for i in range(21)]]
    pygame.draw.polygon(surf, (110, 95, 85), [(px, py - r * .06) for px, py in mouth])
    pygame.draw.polygon(surf, (0, 0, 0, 0) if hole else (35, 20, 18), mouth)
    if not hole:                                               # the oven floor, seen from the front
        pygame.draw.ellipse(surf, (70, 45, 35), (x - r * .5, y + r * .2, r * 1.0, r * .2))
    pygame.draw.rect(surf, (90, 70, 60), (x - r * .7, y + r * .34, r * 1.4, r * .08))


def oven_sprite(hole=False):
    return gfx.cached(("stoneoven", hole), lambda: gfx.icon_sprite(lambda s, c, r: _oven(s, c, r, hole), 150,
                                                                  pad=1.45, outline=5, depth=0.12))


def _eater(surf, c, r, mouth=0.0, happy=False):
    """The Italian pizza chef who tastes the pizza: tall white chef's hat, bushy moustache, big
    round nose, green shirt and a white apron. mouth: 0 closed .. 1 wide open."""
    x, y = c
    skin, brown = (248, 196, 150), (80, 50, 30)
    # body: green shirt and white apron (with a little tomato stain)
    pygame.draw.ellipse(surf, (60, 160, 70), (x - r * 1.05, y + r * .55, r * 2.1, r * 1.3))
    pygame.draw.polygon(surf, (45, 130, 55), [(x - r * .3, y + r * .55), (x, y + r * .85), (x + r * .3, y + r * .55)])
    pygame.draw.rect(surf, (250, 250, 252), (x - r * .55, y + r * .82, r * 1.1, r * .6), border_radius=int(r * .12))
    pygame.draw.circle(surf, (215, 80, 60), (int(x - r * .25), int(y + r * 1.1)), int(r * .08))
    pygame.draw.circle(surf, (215, 80, 60), (int(x - r * .15), int(y + r * 1.18)), int(r * .045))
    # head
    for sd in (-1, 1):                                        # ears
        pygame.draw.circle(surf, skin, (int(x + sd * r * .74), int(y + r * .02)), int(r * .16))
    pygame.draw.ellipse(surf, skin, (x - r * .78, y - r * .62, r * 1.56, r * 1.3))
    # chef's hat: a band and a big puffy top
    for dx, dy, rr in ((-.42, -1.0, .36), (.42, -1.0, .36), (0, -1.15, .44), (-.18, -.92, .34), (.2, -.92, .34)):
        pygame.draw.circle(surf, (252, 252, 255), (int(x + dx * r), int(y + dy * r)), int(rr * r))
    pygame.draw.rect(surf, (240, 240, 248), (x - r * .66, y - r * .78, r * 1.32, r * .3), border_radius=int(r * .1))
    pygame.draw.line(surf, (210, 210, 225), (x - r * .62, y - r * .5), (x + r * .62, y - r * .5), max(2, int(r * .03)))
    # eyes and bushy brows
    for sd in (-1, 1):
        ex, ey = x + sd * r * .3, y - r * .2
        pygame.draw.ellipse(surf, brown, (ex - r * .2, ey - r * .26, r * .4, r * .12))
        if happy:
            pygame.draw.arc(surf, (40, 30, 30), (ex - r * .13, ey - r * .08, r * .26, r * .2), .3, math.pi - .3,
                            max(3, int(r * .06)))
        else:
            pygame.draw.ellipse(surf, (255, 255, 255), (ex - r * .12, ey - r * .12, r * .24, r * .24))
            pygame.draw.circle(surf, (60, 40, 30), (int(ex), int(ey + r * .02)), int(r * .075))
            pygame.draw.circle(surf, (255, 255, 255), (int(ex - r * .025), int(ey - r * .01)), max(2, int(r * .025)))
        pygame.draw.circle(surf, (245, 140, 130), (int(x + sd * r * .5), int(y + r * .2)), int(r * .13))   # cheeks
    # mouth under the moustache: open while eating, a big smile otherwise
    mh = r * (.06 + .34 * mouth)
    m = pygame.Rect(0, 0, r * (.36 + .1 * mouth), mh)
    m.midtop = (int(x), int(y + r * .34))
    if mouth > .1:
        pygame.draw.ellipse(surf, (120, 30, 40), m)
        pygame.draw.ellipse(surf, (240, 110, 120), (m.x + m.w * .2, m.y + m.h * .5, m.w * .6, m.h * .45))
    else:
        pygame.draw.arc(surf, (120, 40, 40), (x - r * .26, y + r * .18, r * .52, r * .34), math.pi * 1.1,
                        math.pi * 1.9, max(3, int(r * .06)))
    # big curly moustache and the round nose on top
    for sd in (-1, 1):
        pygame.draw.polygon(surf, brown, ellipse_pts(x + sd * r * .24, y + r * .27, r * .27, r * .11, sd * -.25, 24))
        pygame.draw.circle(surf, brown, (int(x + sd * r * .5), int(y + r * .2)), int(r * .08))
    pygame.draw.circle(surf, (238, 150, 115), (int(x), int(y + r * .1)), int(r * .17))
    pygame.draw.circle(surf, (250, 190, 160), (int(x - r * .05), int(y + r * .05)), int(r * .05))


def eater_sprite(mouth, happy=False):
    m = round(mouth * 4) / 4
    return gfx.cached(("chef", m, happy), lambda: gfx.icon_sprite(
        lambda s, c, r: _eater(s, c, r, m, happy), 110, pad=1.6, outline=5, depth=0.2))


def _blender(surf, c, r):
    """Hand blender: a body with a button, a metal stick and the blade guard (for the tomatoes)."""
    x, y = c
    pygame.draw.rect(surf, (230, 90, 70), (x - r * .22, y - r * 1.0, r * .44, r * .8), border_radius=int(r * .18))
    pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y - r * .72)), int(r * .08))
    pygame.draw.rect(surf, (190, 195, 210), (x - r * .07, y - r * .2, r * .14, r * .85))
    pygame.draw.ellipse(surf, (170, 175, 195), (x - r * .3, y + r * .55, r * .6, r * .35))


def _grater(surf, c, r):
    """Box grater with holes (for the cheese)."""
    x, y = c
    pygame.draw.polygon(surf, (200, 205, 220), [(x - r * .4, y + r * .9), (x + r * .4, y + r * .9),
                                                (x + r * .3, y - r * .8), (x - r * .3, y - r * .8)])
    pygame.draw.rect(surf, (60, 60, 70), (x - r * .2, y - r * 1.05, r * .4, r * .28), border_radius=int(r * .1))
    for row in range(6):
        for col in range(3):
            pygame.draw.ellipse(surf, (120, 125, 140), (x - r * .22 + col * r * .16, y - r * .6 + row * r * .24,
                                                        r * .1, r * .06))


def tool_sprite(kind):
    draw = {"blender": _blender, "grater": _grater, "knife": icon_knife}[kind]
    return gfx.cached(("tool", kind), lambda: gfx.icon_sprite(draw, 50, pad=1.3, outline=3, depth=0.2))


def _pot(surf, c, r, sauce=True):
    """Bowl with tomato sauce (sauce=True) or grated cheese."""
    _bowl(surf, c, r)
    x, y = c
    if sauce:
        pygame.draw.ellipse(surf, (205, 45, 35), (x - r * .85, y - r * .28, r * 1.7, r * .42))
        for dx in (-.4, .1, .45):
            pygame.draw.circle(surf, (235, 90, 70), (int(x + dx * r), int(y - r * .1)), int(r * .07))


def melted_cheese_sprite(spot=False):
    """A soft pool of melted cheese (some with a golden-brown bubble). Neighbours flow together."""
    def draw(s, c, r):
        x, y = c
        for dx, dy, k in ((0, 0, 1.0), (.45, .3, .6), (-.4, .35, .55), (.1, -.45, .5)):   # a runny blob
            pygame.draw.circle(s, (255, 226, 125), (int(x + dx * r), int(y + dy * r)), int(r * k * .8))
        if spot:
            pygame.draw.circle(s, (228, 160, 70), (int(x + r * .15), int(y - r * .1)), int(r * .22))
    return gfx.cached(("melt", spot), lambda: gfx.icon_sprite(draw, 22, pad=1.3, outline=0, depth=0.12, shadow=0))


def cutter_wheel_sprite():
    """The round blade of the pizza cutter (rotated while it rolls)."""
    def draw(s, c, r):
        x, y = c
        pygame.draw.circle(s, (205, 210, 225), (int(x), int(y)), int(r))
        pygame.draw.circle(s, (160, 165, 185), (int(x), int(y)), int(r * .75), max(2, int(r * .06)))
        for k in range(6):                                    # spokes, so the turning can be seen
            a = k * math.pi / 3
            pygame.draw.line(s, (170, 175, 195), (x, y), (x + math.cos(a) * r * .7, y + math.sin(a) * r * .7),
                             max(2, int(r * .08)))
        pygame.draw.circle(s, (230, 70, 60), (int(x), int(y)), int(r * .22))
    return gfx.cached(("cutwheel",), lambda: gfx.icon_sprite(draw, 30, pad=1.1, outline=3, depth=0.25))


def cutter_handle_sprite():
    def draw(s, c, r):
        x, y = c
        pygame.draw.line(s, (180, 185, 200), (x - r * .95, y + r * .95), (x - r * .3, y + r * .3), max(3, int(r * .14)))
        pygame.draw.line(s, (230, 70, 60), (x - r * .35, y + r * .35), (x + r * .9, y - r * .9), max(6, int(r * .3)))
    return gfx.cached(("cuthandle",), lambda: gfx.icon_sprite(draw, 50, pad=1.1, outline=3, depth=0.25))


def heart_sprite():
    return gfx.cached(("pheart",), lambda: gfx.icon_sprite(
        lambda s, c, r: pygame.draw.polygon(s, (240, 70, 110), heart_pts(c, r)), 22, pad=1.2, outline=3, shadow=40))


def ladle_sprite():
    def draw(s, c, r):
        x, y = c
        pygame.draw.line(s, (180, 185, 200), (x + r * .2, y + r * .1), (x + r * .9, y - r * .8), max(3, int(r * .12)))
        pygame.draw.ellipse(s, (180, 185, 200), (x - r * .7, y - r * .25, r * 1.1, r * .75))
        pygame.draw.ellipse(s, (205, 45, 35), (x - r * .6, y - r * .2, r * .9, r * .5))
    return gfx.cached(("ladle",), lambda: gfx.icon_sprite(draw, 34, pad=1.2, outline=3, depth=0.2))


def pot_sprite(sauce=True):
    return gfx.cached(("pot", sauce), lambda: gfx.icon_sprite(lambda s, c, r: _pot(s, c, r, sauce), 78,
                                                             pad=1.15, outline=4, depth=0.2))


def draw_pizza_icon(surf, c, r):
    pygame.draw.circle(surf, (232, 182, 100), c, r)
    pygame.draw.circle(surf, (208, 66, 44), c, int(r * 0.8))
    for dx, dy in ((-.3, -.25), (.32, -.1), (-.05, .35), (.1, -.42)):
        pygame.draw.circle(surf, (120, 35, 35), (int(c[0] + dx * r), int(c[1] + dy * r)), int(r * 0.2))
        pygame.draw.circle(surf, (200, 70, 62), (int(c[0] + dx * r), int(c[1] + dy * r)), int(r * 0.16))
    pygame.draw.circle(surf, (250, 226, 120), (int(c[0] + .38 * r), int(c[1] + .32 * r)), int(r * 0.1))


def icon_oven(surf, c, r):
    _oven(surf, (c[0], c[1] + r * .05), r * .62)


def icon_knife(surf, c, r):
    x, y = c
    pygame.draw.polygon(surf, (215, 220, 235), [(x - r * .9, y - r * .1), (x + r * .3, y - r * .3),
                                                (x + r * .3, y + r * .15), (x - r * .9, y + r * .05)])
    pygame.draw.rect(surf, (120, 70, 40), (x + r * .3, y - r * .22, r * .7, r * .32), border_radius=int(r * .1))


# --------------------------------------------------------------------- Spiel ---

class Bin:
    def __init__(self, kind, center):
        self.kind, self.c, self.r = kind, center, 60
        self.progress, self.hover, self.armed = 0.0, False, True


class PizzaGame(Game):
    title = "Pizza backen"
    theme = (255, 160, 60)
    show_stars = False               # the happy customer is the reward

    @staticmethod
    def icon(surf, c, r):
        draw_pizza_icon(surf, c, int(r * 0.9))

    def on_restart(self):
        self.toppings = []             # (kind, x, y, sprite) in screen pixels
        self.phase, self.phase_t, self.timer = "decorate", 0.0, 0.0
        self.center = (self.W * 0.5, self.H * 0.6)
        ys = (0.44, 0.72)                         # tomato + cheese left, salami + mushroom right
        self.bins = [Bin(k, (self.W * (0.1 if i < 2 else 0.9), self.H * ys[i % 2]))
                     for i, k in enumerate(KINDS)]
        # the oven is a button like "play again" (top right): press it when the pizza is ready
        self.oven = DwellButton((self.W - 150, 100), 56, 1.2, icon_oven, color=(255, 150, 60))
        self.station = (self.W * 0.5, 118)        # cutting board / bowl, above the pizza
        self.item = None                          # dict(kind, work, t): being cut / mashed / grated
        self.bowl = None                          # dict(kind, mode, left): pieces, sauce or cheese ready
        self.carry = {}                           # hand -> dict(kind, mode, still, last)
        z = (R + 60) * 2
        self.sauce = pygame.Surface((z, z), pygame.SRCALPHA)   # the sauce the player smeared on
        self.sauce_dabs = 0
        self.hist = {}
        self.last_chop = -9.0
        self.drops = []                           # (x, y, age) little bounce when a piece lands
        self.push = 0.0                           # 0 = pizza on the table .. 1 = inside the oven
        self.grab = None                          # the hand pushing the pizza into the oven
        self.grab_rel = 0.0                       # where on the pizza it pushes (px at full size)
        self.push_idle = 0.0                      # seconds the pizza has not moved towards the oven
        self.tool_hand = None                     # the hand that holds the knife / the cheese for grating
        self.tool_lost = 0.0
        self.eaten = 0
        self.hearts = []                          # (x, y, age) rising after "mmmh"
        self.hint_t, self._hint_key = 0.0, None   # time without progress (for the ghost hand)
        self._sprites = {}
        self._result_pie = self._pie_key = self._deco_key = None

    # ---- hands ----
    def _hands(self, pose):
        """One point per hand (finger, else wrist) for everyone: {"r": (x, y), "l#1": ...}"""
        out = {}
        for p in (pose.all if pose else []):
            for s in "lr":
                for part in ("idx", "wr"):
                    if p.vis(f"{s}_{part}") >= 0.35:
                        out[s if p.slot == 0 else f"{s}#{p.slot}"] = tuple(p.P(f"{s}_{part}"))
                        break
        return out

    def _velocity(self, hands):
        vel = {}
        for n, (x, y) in hands.items():
            h = self.hist.setdefault(n, deque())
            h.append((self.t, x, y))
            while h and self.t - h[0][0] > 0.15:
                h.popleft()
            dt = h[-1][0] - h[0][0]
            vel[n] = ((h[-1][1] - h[0][1]) / dt, (h[-1][2] - h[0][2]) / dt) if dt > 0.02 else (0.0, 0.0)
        for n in list(self.hist):
            if n not in hands:
                del self.hist[n]
        return vel

    # ---- helpers ----
    def _sprite(self, kind, angle):
        key = (kind, angle)
        if key not in self._sprites:
            size = 34 if kind == "cheese" else S                # grated cheese: small, fine shreds
            self._sprites[key] = pygame.transform.rotozoom(topping_sprite(kind, size), angle, 1)
        return self._sprites[key]

    def _place(self, kind, pos, quiet=False):
        # grated cheese has its own (bigger) limit: sprinkling it must never block the pieces
        cheese = kind == "cheese"
        if sum(1 for t in self.toppings if (t[0] == "cheese") == cheese) >= (MAX_CHEESE if cheese else MAX_TOPPINGS):
            if not quiet:
                self.ctx.play("boing")
            return False
        cx, cy = self.center
        dx, dy = pos[0] - cx, pos[1] - cy
        d = math.hypot(dx, dy)
        lim = R - 30
        if d > lim:
            dx, dy = dx / d * lim, dy / d * lim
        sprite = self._sprite(kind, random.choice(range(0, 360, 30)))
        self.toppings.append((kind, cx + dx, cy + dy, sprite))
        if not quiet:
            self.drops.append((cx + dx, cy + dy, 0.0))
            self.ctx.play("poof")
            self.particles.burst((cx + dx, cy + dy), 6, [(255, 255, 255), (255, 232, 140)], 140, 0.4, (2, 5), 300)
        return True

    def _dab(self, pos):
        """Smear a bit of tomato sauce onto the dough (it stays inside the crust)."""
        cx, cy = self.center
        c = self.sauce.get_width() // 2
        dx, dy = pos[0] - cx, pos[1] - cy
        d = math.hypot(dx, dy)
        lim = R - 28 - DAB_R * 0.5
        if d > lim:
            dx, dy = dx / d * lim, dy / d * lim
        shade = random.randint(-12, 12)
        pygame.draw.circle(self.sauce, (205 + shade, 48 + shade // 2, 36, 255), (int(c + dx), int(c + dy)),
                           DAB_R + random.randint(-4, 4))
        pygame.draw.circle(self.sauce, (228, 85, 62, 255), (int(c + dx - 6), int(c + dy - 6)), 5)
        self.sauce_dabs += 1

    def sauce_coverage(self):
        """0..1: how much of the dough has sauce on it."""
        if not self.sauce_dabs:
            return 0.0
        a = pygame.surfarray.array_alpha(self.sauce)
        c = a.shape[0] // 2
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        inside = (xx - c) ** 2 + (yy - c) ** 2 <= (R - 28) ** 2
        return float((a[inside] > 0).mean())

    def _pizza_pos(self):
        """Pizza centre and scale while it travels into the oven (push 0..1)."""
        k = ease_out_cubic(min(1.0, self.push))
        ox, oy = self._oven_mouth()
        x = self.center[0] + (ox - self.center[0]) * k
        y = self.center[1] + (oy - self.center[1]) * k
        return (x, y), 1.0 - 0.6 * k                           # small enough for the oven mouth

    def _pizza_tilt(self):
        """How flat the pizza looks: on the table we look down on it, in the oven from the
        front - it is squashed to a flat ellipse lying on the oven floor (3D look)."""
        return 1.0 - 0.68 * ease_out_cubic(min(1.0, self.push))

    def _oven_pos(self):
        slide = ease_out_back(min(1.0, self.phase_t / 0.6)) if self.phase == "to_oven" else 1.0
        if self.phase in ("slice", "eat"):
            slide = max(0.0, 1 - self.phase_t / 0.5) if self.phase == "slice" else 0.0
        return (self.W + 260 - (self.W * 0.2 + 260) * slide, self.H * 0.52)

    def _oven_mouth(self):
        """Where the pizza lies inside: on the oven floor, just behind the mouth."""
        x, y = self._oven_pos()
        return (x, y + 150 * .27)

    # ---- flow ----
    def play_update(self, dt, pose, hands_all):
        self.phase_t += dt
        hands = self._hands(pose)
        vel = self._velocity(hands)
        self.drops = [(x, y, a + dt) for x, y, a in self.drops if a + dt < 0.35]
        if self.phase == "decorate":
            self._decorate(dt, hands, vel)
        elif self.phase == "to_oven":
            self._to_oven(dt, hands)
        elif self.phase == "bake":
            if random.random() < 0.5:                        # smoke from the chimney
                x, y = self._oven_pos()
                self.particles.burst((x + 105, y - 210), 1, [(235, 235, 240), (210, 210, 220)], 30, 1.4, (8, 14), -60)
            if int(self.phase_t) != int(self.phase_t - dt) and self.phase_t < BAKE_TIME:
                self.ctx.play("tick")
            if self.phase_t >= BAKE_TIME:
                self.ctx.play("chime")
                self.phase, self.phase_t = "out", 0.0
        elif self.phase == "out":
            self.push = max(0.0, 1 - self.phase_t / 1.0)
            if self.phase_t >= 1.0:
                self.push = 0.0
                self.phase, self.phase_t = "slice", 0.0
        elif self.phase == "slice":                         # the pizza cutter rolls across 4 times
            for k in range(4):
                if self.phase_t - dt < k * SLICE_CUT + 0.01 <= self.phase_t:
                    self.ctx.play("cut")
            if self.phase_t >= 4 * SLICE_CUT + 0.4:
                self.phase, self.phase_t = "eat", 0.0
                self.ctx.play("boing")
        elif self.phase == "eat":
            # the customer takes ONE slice: om-nom-nom (3 bites), then "mmmh!" with hearts
            t, mx, my = self.phase_t, *self._eater_pos()
            if t >= EAT_TAKE - SLICE_LIFT and self.eaten == 0:
                self.eaten = 1                              # the cut slice lifts off: the gap appears now
                self.ctx.play("whoosh")
            if t - dt < EAT_TAKE <= t:
                self.ctx.play("omnom")                      # (only with an own recording)
            for bt in EAT_BITES:
                if t - dt < bt <= t:
                    self.ctx.play("bite")
                    self.particles.burst((mx, my + 50), 8, [(232, 182, 100), (208, 66, 44), (255, 230, 120)],
                                         200, 0.6, (3, 6), 600)
            if t - dt < EAT_YUM <= t:
                self.ctx.play("mmh")                        # (only with an own recording)
                self.ctx.play("gold")                       # a happy little fanfare
                self.hearts = [(mx + random.uniform(-80, 80), my - 60 - random.uniform(0, 40), -random.uniform(0, 0.6))
                               for _ in range(6)]
            self.hearts = [(x, y - 70 * dt, a + dt) for x, y, a in self.hearts if a + dt < 1.6]
            if t >= EAT_END:
                pieces = [p for p in self.toppings if p[0] != "cheese"]
                kinds = len({p[0] for p in self.toppings}) + (1 if self.sauce_dabs else 0)
                score = len(pieces) + 3 * kinds + int(10 * self.sauce_coverage())
                self.ctx.log("pizza", pieces=len(pieces), kinds=kinds, sauce=round(self.sauce_coverage(), 2))
                self.finish(1 + min(4, score // 8))

    def _decorate(self, dt, hands, vel):
        self.timer += dt
        lv = self.ctx.level
        # any progress (a pick, a cut, a piece or a dab of sauce) resets the hint clock
        key = (self.item and (self.item["kind"], self.item["work"]), self.bowl and self.bowl["left"],
               len(self.toppings), self.sauce_dabs, tuple(sorted(self.carry)))
        self.hint_t = self.hint_t + dt if key == self._hint_key else 0.0
        self._hint_key = key
        # 1) pick a whole ingredient from the side
        for b in self.bins:
            # any hand can pick - also one that still holds something (play-test bug report)
            b.hover = any(math.hypot(x - b.c[0], y - b.c[1]) <= b.r * 1.1 for x, y in hands.values())
            if not b.hover:
                b.armed, b.progress = True, max(0.0, b.progress - dt * 2)
            elif b.armed:
                b.progress += dt / PICK_TIME
                if b.progress >= 1.0:
                    b.progress, b.armed = 0.0, False
                    self.item, self.bowl = dict(kind=b.kind, work=0, t=0.0), None
                    self.carry.clear()
                    self.tool_hand = None
                    self.ctx.play("whoosh")
                    self.ctx.log("pick", ingredient=b.kind)
        sx, sy = self.station
        # 2) make it ready: the knife wants a fast stroke down, the grater any up/down stroke,
        #    the blender (tomatoes) runs by itself
        if self.item and TOOL.get(self.item["kind"]) == "blender":
            self.item["t"] += dt
            self._blend(dt)
        elif self.item:
            self.item["t"] += dt
            tool = TOOL.get(self.item["kind"], "knife")
            # the hand that comes to the board takes the knife (or the piece of cheese) by itself -
            # no extra "grab" step (MANIFEST: every step without explanation); only that hand
            # works, and if the camera loses it only for a moment, the tool stays in it
            if self.tool_hand is not None and self.tool_hand not in hands:
                self.tool_lost += dt
                if self.tool_lost > 0.6:
                    self.tool_hand = None
            else:
                self.tool_lost = 0.0
            if self.tool_hand is None:
                rx, ry = self._tool_rest(tool)
                for n, (x, y) in hands.items():
                    if math.hypot(x - rx, y - ry) < TAKE_REACH or (abs(x - sx) < 190 and sy - 140 < y < sy + 110):
                        self.tool_hand = n
                        self.ctx.play("click")
                        break
            for n, (x, y) in hands.items():
                if n != self.tool_hand:
                    continue
                vx, vy = vel.get(n, (0.0, 0.0))
                fast = (vy > CHOP_SPEED[lv] and abs(vx) < vy * 1.5) if tool != "grater" else \
                    (abs(vy) > CHOP_SPEED[lv] * 0.6 and abs(vx) < abs(vy) * 1.5)
                # the knife also cuts by just being held over the ingredient (no chop needed)
                hover_cut = False
                if tool == "knife":
                    cx_, cy_ = self._cut_point()
                    if math.hypot(x - cx_, y - (cy_ - 30)) < CUT_REACH:
                        self.item["hover"] = self.item.get("hover", 0.0) + dt
                        hover_cut = self.item["hover"] >= HOVER_CUT[lv]
                    else:
                        self.item["hover"] = max(0.0, self.item.get("hover", 0.0) - dt * 2)
                chop = (abs(x - sx) < 190 and sy - 140 < y < sy + 110 and fast
                        and self.t - self.last_chop > (CHOP_GAP if tool != "grater" else 0.18))
                if chop or hover_cut:
                    self.last_chop = self.t
                    self.item["hover"] = 0.0
                    self.item["work"] += 1
                    self._work_effect(tool)
                    if self.item["work"] >= WORK[tool]:
                        kind = self.item["kind"]
                        # short wait, so the working hand does not grab something right away
                        if kind == "tomato":
                            self.bowl = dict(kind="tomato", mode="sauce", left=SAUCE_DABS, wait=0.7)
                        elif kind == "cheese":
                            self.bowl = dict(kind="cheese", mode="cheese", left=CHEESE_HANDFULS, wait=0.7)
                        else:
                            self.bowl = dict(kind=kind, mode="piece", left=PIECES, wait=0.7)
                        self.item = self.tool_hand = None
                        self.ctx.play("chime")
                    break
        # 3) from the bowl onto the pizza: pieces are carried and put down by holding still,
        #    sauce is smeared and cheese sprinkled where the hand moves over the pizza
        if self.bowl:
            self.bowl["wait"] = max(0.0, self.bowl.get("wait", 0.0) - dt)
            for n, (x, y) in hands.items():
                if (n not in self.carry and self.bowl["left"] > 0 and self.bowl["wait"] <= 0
                        and math.hypot(x - sx, y - sy) < 95):
                    self.carry[n] = dict(kind=self.bowl["kind"], mode=self.bowl["mode"], still=0.0, last=None)
                    if self.bowl["mode"] == "piece":
                        self.bowl["left"] -= 1
                    self.ctx.play("click")
        cx, cy = self.center
        for n in list(self.carry):
            c = self.carry[n]
            if n not in hands:
                c["lost"] = c.get("lost", 0.0) + dt
                if c["lost"] > 1.0:                         # hand gone: the piece goes back
                    if c["mode"] == "piece" and self.bowl and self.bowl["kind"] == c["kind"]:
                        self.bowl["left"] += 1
                    del self.carry[n]
                continue
            c["lost"] = 0.0
            x, y = hands[n]
            over = math.hypot(x - cx, y - cy) < R - 10
            if c["mode"] == "piece":
                speed = math.hypot(*vel.get(n, (0.0, 0.0)))
                if over and speed < STILL_SPEED:
                    c["still"] += dt
                    if c["still"] >= PLACE_TIME:
                        self._place(c["kind"], (x, y))
                        del self.carry[n]
                else:
                    c["still"] = max(0.0, c["still"] - dt * 2)
                continue
            if not over or not self.bowl or self.bowl["left"] <= 0:
                c["last"] = None
                if not self.bowl or self.bowl["left"] <= 0:
                    del self.carry[n]
                continue
            step = 10 if c["mode"] == "sauce" else 18
            if c["last"] is None or math.hypot(x - c["last"][0], y - c["last"][1]) >= step:
                c["last"] = (x, y)
                self.bowl["left"] -= 1
                if c["mode"] == "sauce":
                    self._dab((x, y))
                    if self.sauce_dabs % 7 == 1:
                        self.ctx.play("squish")
                else:
                    for _ in range(2):
                        self._place("cheese", (x + random.uniform(-26, 26), y + random.uniform(-26, 26)), quiet=True)
                    if self.bowl["left"] % 5 == 0:
                        self.ctx.play("pop5")
        if self.bowl and self.bowl["left"] <= 0 and not any(c["mode"] == "piece" for c in self.carry.values()):
            self.bowl = None
        # 4) into the oven: a button like "play again", whenever there is something on the pizza
        ready = bool(self.toppings) or self.sauce_dabs > 0
        if self.oven.update(dt, list(hands.values())):
            if not ready:                                   # nothing on the dough yet
                self.ctx.play("boing")
                return
            self.phase, self.phase_t = "to_oven", 0.0
            self.item, self.bowl = None, None
            self.carry.clear()
            self.ctx.play("whoosh")

    def _tool_rest(self, tool):
        """Where the knife / the cheese waits until a hand takes it. The knife hovers right over
        the spot of the next cut, so the hand that takes it is already where it cuts."""
        sx, sy = self.station
        if tool == "knife" and self.item:
            x, y = self._cut_point()
            return (x - 8, y - 40)
        return (sx + 175, sy + 10) if tool == "knife" else (sx - 75, sy - 5)

    def _cut_right(self):
        """x where what is left of the ingredient ends: every cut takes a slice off the visible
        part (the sprite has see-through margins, they do not count)."""
        bb = whole_sprite(self.item["kind"]).get_bounding_rect()
        return self.station[0] - 110 + bb.right - bb.width * CUT_FRAC * self.item["work"]

    def _cut_point(self):
        """Where the next cut goes through the ingredient (a slice's width in from its end)."""
        bb = whole_sprite(self.item["kind"]).get_bounding_rect()
        return (self._cut_right() - CUT_FRAC * bb.width * 0.8, self.station[1] - 12)

    def _blend(self, dt):
        """Tomatoes -> sauce: the blender does it by itself (play-test: a hand motion for it felt
        strange) - a short whirring show, then the pot of sauce is there to spread."""
        if self.item["work"] == 0 and not self.item.get("started"):
            self.item["started"] = True
            self.ctx.play("blend")
        self.item["spin"] = self.item.get("spin", 0.0) + dt * 14
        work = min(WORK["blender"], int(self.item["t"] / BLEND_TIME * WORK["blender"]))
        while self.item["work"] < work:
            self.item["work"] += 1
            sx, sy = self.station
            self.particles.burst((sx, sy + 10), 6, [(220, 40, 35), (240, 90, 70)], 200, 0.45, (3, 6), 700)
        if self.item["t"] >= BLEND_TIME:
            self.bowl = dict(kind="tomato", mode="sauce", left=SAUCE_DABS, wait=0.3)
            self.item = None
            self.ctx.play("chime")

    def _work_effect(self, tool):
        sx, sy = self.station
        if tool == "knife":
            self.ctx.play("cut")
            self.particles.burst((sx, sy), 8, [(255, 255, 255), (230, 230, 240)], 220, 0.35, (2, 5), 600)
        else:
            self.ctx.play("grate")
            self.particles.burst((sx + 40, sy + 40), 6, [(255, 220, 90), (250, 200, 60)], 120, 0.5, (2, 4), 500)

    def _to_oven(self, dt, hands):
        """The child pushes the pizza into the oven itself: a hand on the pizza takes it along
        towards the oven. It only goes forwards (never slides back) and stays where it is let go,
        so it can be pushed in several goes; the hand may touch it anywhere, also at the edge."""
        (px, py), sc = self._pizza_pos()
        if self.phase_t < 0.6:                              # the oven is still sliding in
            return
        self.push_idle += dt
        if self.grab and self.grab not in hands:            # hand lost by the camera: let go
            self.grab = None
        if not self.grab:
            for n, (x, y) in hands.items():
                if math.hypot(x - px, y - py) < R * sc * 1.25:
                    self.grab, self.grab_rel = n, (px - x) / sc     # where on the pizza the hand is
                    self.ctx.play("click")
                    break
        if self.grab:
            x, y = hands[self.grab]
            want_x = x + self.grab_rel * sc                 # where the hand would put the pizza
            if math.hypot(want_x - px, y - py) > R * 0.9 + 60:
                self.grab = None                            # the hand went away: the pizza stays
            else:
                cx, ox = self.center[0], self._oven_mouth()[0]
                u = min(1.0, max(0.0, (want_x - cx) / (ox - cx)))
                goal = 1 - (1 - u) ** (1 / 3)               # undo the easing in _pizza_pos
                if goal > self.push:
                    self.push = min(1.0, self.push + min(goal - self.push, dt * PUSH_SPEED))
                    self.push_idle = 0.0
        if self.push >= 0.92:
            self.push = 1.0
            self.grab = None
            self.phase, self.phase_t = "bake", 0.0
            self.ctx.play("whoosh")

    def _eater_pos(self):
        """The hungry boy pops up from below, right next to the pizza."""
        rise = ease_out_back(min(1.0, self.phase_t / 0.6)) if self.phase == "eat" else 1.0
        top = self.H * 0.55
        return (self.W * 0.8, self.H + 170 - (self.H + 170 - top) * rise)

    # ---- drawing ----
    def _pie_surface(self, baked=0.0, eaten=0, cuts=0):
        """Pizza with toppings as one surface (centre = surface centre). The sauce is always the
        bottom layer; everything else lies in the order it was put on. While baking, each bit of
        cheese melts into a soft golden pool at its own place in that order."""
        base = pizza_base()
        tmp = base.copy()
        c = base.get_width() // 2
        cx, cy = self.center
        if self.sauce_dabs:
            tmp.blit(self.sauce, self.sauce.get_rect(center=(c, c)))
        melt_a = int(225 * min(1.0, baked * 1.4))             # a little see-through: pools run together
        shred_a = int(255 * (1 - baked))
        for i, (kind, x, y, sprite) in enumerate(self.toppings):
            pos = (c + x - cx, c + y - cy)
            if kind != "cheese" or baked <= 0:
                tmp.blit(sprite, sprite.get_rect(center=pos))
                continue
            blob = melted_cheese_sprite(i % 5 == 0)
            blob.set_alpha(melt_a)
            tmp.blit(blob, blob.get_rect(center=pos))
            if shred_a > 0:
                sprite.set_alpha(shred_a)
                tmp.blit(sprite, sprite.get_rect(center=pos))
                sprite.set_alpha(255)
        if baked > 0:                                       # golden brown, a bit more at the crust
            tmp.fill((255, int(255 - 45 * baked), int(255 - 105 * baked)), special_flags=pygame.BLEND_RGB_MULT)
            crust = pygame.Surface(tmp.get_size(), pygame.SRCALPHA)
            for i in range(6):
                pygame.draw.circle(crust, (140, 80, 25, int(28 * baked)), (c, c), R - i * 4, 7)
            tmp.blit(crust, (0, 0))
        if cuts:
            for i in range(cuts):
                a = i * math.pi / 4
                dx, dy = math.cos(a) * R, math.sin(a) * R
                pygame.draw.line(tmp, (120, 60, 30), (c - dx, c - dy), (c + dx, c + dy), 4)
        if eaten:
            for i in range(eaten):                          # eaten slices leave the board empty
                a0 = (i - 2) * math.pi / 4
                pts = [(c, c)] + [(c + math.cos(a0 + k * math.pi / 16) * (R + 4), c + math.sin(a0 + k * math.pi / 16) * (R + 4))
                                  for k in range(5)]
                pygame.draw.polygon(tmp, (176, 120, 70), pts)
                for k in range(3):                          # crumbs
                    a = a0 + random.Random(i * 7 + k).uniform(0, math.pi / 4)
                    d = random.Random(i * 11 + k).uniform(30, R - 20)
                    pygame.draw.circle(tmp, (230, 180, 100), (int(c + math.cos(a) * d), int(c + math.sin(a) * d)), 4)
        return tmp

    def play_draw(self, surf, pose):
        if self.phase == "decorate":
            self._draw_decorate(surf, pose)
            return
        # oven, pizza travelling, baking, slicing, eating
        ovx, ovy = self._oven_pos()
        if self.phase in ("to_oven", "bake", "out", "slice"):
            gfx.blit_center(surf, oven_sprite(), (ovx, ovy))
        (px, py), sc = self._pizza_pos()
        baked = 0.0
        if self.phase == "bake":
            baked = min(1.0, self.phase_t / BAKE_TIME)
        elif self.phase in ("out", "slice", "eat"):
            baked = 1.0
        cuts = 0
        if self.phase == "slice":
            cuts = min(4, int(self.phase_t / SLICE_CUT))
        elif self.phase == "eat":
            cuts = 4
        key = (round(baked * 14) / 14, cuts, self.eaten if self.phase == "eat" else 0, len(self.toppings),
               self.sauce_dabs)
        if getattr(self, "_pie_key", None) != key:
            self._pie_key = key
            self._pie = self._pie_surface(key[0], key[2], key[1])
        tilt = self._pizza_tilt()
        in_oven = self.phase in ("to_oven", "bake", "out")
        if in_oven:                                                  # fire at the back of the oven
            mx, my = self._oven_mouth()
            heat = 1.0 if self.phase == "bake" else 0.5
            for i in range(6):
                fx = mx - 55 + i * 22 + math.sin(self.t * 9 + i) * 5
                h = (26 + 18 * (0.5 + 0.5 * math.sin(self.t * 11 + i * 1.7))) * heat
                gfx.add_glow(surf, (fx, my - 34 - h * .4), int(h * .8), (255, 110, 20), 0.6)
                gfx.add_glow(surf, (fx, my - 30 - h * .2), int(h * .45), (255, 210, 110), 0.5)
        if self.phase == "to_oven" and self.push < 0.6:              # wooden peel handle, under the pizza
            hx = px - R * sc - 120 * sc
            pygame.draw.line(surf, (110, 70, 40), (hx, py + 6), (px, py + 6), max(6, int(22 * sc)))
            pygame.draw.line(surf, (170, 120, 70), (hx, py), (px, py), max(4, int(14 * sc)))
        gfx.blit_center(surf, self._pie, (px, py), scale=sc, sy=tilt)
        if in_oven and self.push > 0.55:
            # the front of the oven (mouth cut out) goes over the pizza: now it is INSIDE
            gfx.blit_center(surf, oven_sprite(hole=True), (ovx, ovy))
        if self.phase == "bake":
            mx, my = self._oven_mouth()
            gfx.add_glow(surf, (mx, my - 20), 110, (255, 140, 40), 0.15 + 0.05 * math.sin(self.t * 7))
            progress_ring(surf, (ovx, ovy - 175), 34, baked, (255, 170, 60), 12)   # baking clock
        if self.phase == "to_oven" and not self.grab and self.phase_t > 0.6:     # "push it in" arrows
            for i in range(3):
                k = (self.t * 1.5 + i / 3) % 1.0
                ax = px + R * sc + 20 + k * 120
                pts = [(ax, py - 26), (ax + 26, py), (ax, py + 26), (ax + 8, py)]
                gfx.add_glow(surf, (ax + 10, py), 34, (255, 200, 90), 0.5 * math.sin(k * math.pi))
                pygame.draw.polygon(surf, (255, 230, 120), pts)
                pygame.draw.aalines(surf, gfx.INK, True, pts)
            if self.push_idle > HINT_AFTER - 1.0:           # a see-through hand pushes it, to show how
                u = (self.t * 0.7) % 1.0
                k = ease_out_cubic(min(1.0, u / 0.7))
                ghost_hand(surf, (px - R * sc * 0.6 + 150 * k, py + 10), self.t)
        if self.phase == "slice" and cuts < 4:
            self._draw_cutter(surf, (px, py), cuts, (self.phase_t % SLICE_CUT) / SLICE_CUT)
        if self.phase == "eat":
            self._draw_eater(surf, (px, py))

    def _draw_cutter(self, surf, centre, i, p):
        """The pizza cutter rolls along cut number i (p = 0..1); the cut appears behind it."""
        px, py = centre
        p = min(1.0, p * 1.15)
        a = i * math.pi / 4
        ux, uy = math.cos(a), math.sin(a)
        x0, y0 = px - ux * (R + 10), py - uy * (R + 10)
        x, y = x0 + ux * (2 * R + 20) * p, y0 + uy * (2 * R + 20) * p
        pygame.draw.line(surf, (120, 60, 30), (px - ux * R, py - uy * R),
                         (px - ux * R + ux * 2 * R * p, py - uy * R + uy * 2 * R * p), 4)
        gfx.blit_center(surf, cutter_handle_sprite(), (x + 46, y - 46))
        gfx.blit_center(surf, cutter_wheel_sprite(), (x, y), angle=-p * 720)

    def _slice_surface(self, bites=0):
        """The slice the chef eats, cut out of THIS baked pizza (the same wedge that leaves the gap,
        see _pie_surface). Same size as the pizza surface, with the slice's tip in its centre, so
        it turns around the tip. bites: that many bites are taken from the tip."""
        key = ("eatslice", bites)
        if key not in self._sprites:
            pie = self._pie_surface(1.0, 0, 4)
            c = pie.get_width() // 2
            a0 = -math.pi / 2                                       # slice 0 of _pie_surface's "eaten"
            pts = [(c, c)] + [(c + math.cos(a0 + k * math.pi / 16) * R, c + math.sin(a0 + k * math.pi / 16) * R)
                              for k in range(5)]
            mask = pygame.Surface(pie.get_size(), pygame.SRCALPHA)
            mask.fill((255, 255, 255, 0))
            pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
            out = pie.copy()
            out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            dx, dy = math.cos(a0 + math.pi / 8), math.sin(a0 + math.pi / 8)     # along the slice
            nx, ny = -dy, dx
            gone = (0, 0, 0, 0)
            if bites:
                pygame.draw.circle(out, gone, (c, c), int(max(0.0, bites * BITE - 0.12) * R))
            for j in range(1, bites + 1):                           # scalloped bite marks
                a = (j * BITE - 0.06) * R
                pygame.draw.circle(out, gone, (int(c + dx * a), int(c + dy * a)), int(0.17 * R))
                for s in (-1, 1):
                    b = a - 0.04 * R
                    pygame.draw.circle(out, gone, (int(c + dx * b + s * nx * 0.13 * R), int(c + dy * b + s * ny * 0.13 * R)),
                                       int(0.12 * R))
            self._sprites[key] = out
        return self._sprites[key]

    def _draw_eater(self, surf, pizza_at):
        px, py = pizza_at
        mx, my = self._eater_pos()
        t = self.phase_t
        mouth, happy = 0.0, t >= EAT_YUM
        k = min(1.0, max(0.0, (t - (EAT_TAKE - SLICE_LIFT)) / SLICE_LIFT))   # 0 on the pizza .. 1 at the mouth
        if t < EAT_TAKE:
            mouth = k                                       # opens wide for the slice
        elif t < EAT_YUM:                                   # chewing: om - nom - nom
            mouth = 0.8 if int((t - EAT_TAKE) * 6) % 2 == 0 else 0.15
        gfx.blit_center(surf, eater_sprite(mouth, happy=happy), (mx, my))
        if self.eaten and t < EAT_YUM:
            # the real slice, cut out of this pizza: it lifts off, flies in an arc and turns its
            # tip up into the mouth; every bite takes a piece and the rest moves up after it
            e = ease_out_cubic(k)
            bites = sum(1 for bt in EAT_BITES if t >= bt)
            scale = 1 - (1 - SLICE_HOLD) * e
            last = max(0.0, (t - EAT_BITES[-1] - 0.2) / 0.3)            # the crust goes in last
            if last < 1:
                depth = max(0.0, bites * BITE - 0.08) * R * scale
                tx, ty = mx, my + 48 - depth                                # tip target: bitten edge at the mouth
                x = px + (tx - px) * e
                y = py + (ty - py) * e - math.sin(k * math.pi) * 70         # a little arc
                spr = pygame.transform.rotozoom(self._slice_surface(bites), SLICE_HANG * e, scale * (1 - last))
                gfx.blit_center(surf, spr, (x, y))
        for x, y, a in self.hearts:                         # hearts rise after "mmmh"
            if a > 0:
                k = min(1.0, a / 0.3) * (1 - max(0.0, (a - 1.2) / 0.4))
                gfx.blit_center(surf, heart_sprite(), (x + math.sin(a * 6) * 8, y), scale=max(0.05, k))

    def _draw_decorate(self, surf, pose):
        cx, cy = self.center
        key = (len(self.toppings), self.sauce_dabs)
        if getattr(self, "_deco_key", None) != key:               # rebuilt only when something lands
            self._deco_pie, self._deco_key = self._pie_surface(), key
        gfx.blit_center(surf, self._deco_pie, (cx, cy))
        for x, y, a in self.drops:                              # landing bounce
            circle_alpha(surf, (255, 255, 255, int(200 * (1 - a / 0.35))), (x, y), 20 + 60 * a, 3)
        # station: the ingredient being made ready, or the bowl with what came out of it
        sx, sy = self.station
        hands = self._hands(pose)
        if self.item:
            self._draw_work(surf, hands)
        elif self.bowl:
            left = self.bowl["left"]
            if self.bowl["mode"] == "sauce":
                gfx.blit_center(surf, pot_sprite(True), (sx, sy + 8))
            else:
                gfx.blit_center(surf, bowl_sprite(), (sx, sy + 8))
                rnd = random.Random(3)
                n = min(left, PIECES) if self.bowl["mode"] == "piece" else min(9, 1 + left // 5)
                for i in range(n):
                    gfx.blit_center(surf, self._sprite(self.bowl["kind"], (i * 60) % 360),
                                    (sx + rnd.uniform(-45, 45), sy - 4 + rnd.uniform(-12, 8)), scale=0.75)
        for b in self.bins:
            k = (1.08 if b.hover else 1.0) * (1 + 0.02 * math.sin(self.t * 3 + b.c[1])) + 0.06 * b.progress
            if b.hover:
                gfx.add_glow(surf, b.c, b.r * 1.9, (255, 220, 160), 0.55)
            gfx.blit_center(surf, button_sprite(b.r, (255, 170, 70), (255, 246, 230)), b.c, scale=k)
            gfx.blit_center(surf, whole_sprite(b.kind, 40), b.c, scale=k)
            progress_ring(surf, b.c, b.r * k + 16, b.progress)
        self.oven.draw(surf, self.t)                            # always there, top right
        if self.hint_t > HINT_AFTER:
            self._draw_hint(surf)
        # what the hands carry: a piece (ring fills while held still over the pizza),
        # a ladle of sauce, or a handful of grated cheese
        for n, c in self.carry.items():
            if n not in hands:
                continue
            x, y = hands[n]
            bob = 4 * math.sin(self.t * 8)
            if c["mode"] == "piece":
                gfx.blit_center(surf, self._sprite(c["kind"], 0), (x, y - 30 + bob), scale=1.15)
                progress_ring(surf, (x, y - 30), 46, c["still"] / PLACE_TIME, (120, 230, 120), 10)
            elif c["mode"] == "sauce":
                gfx.blit_center(surf, ladle_sprite(), (x + 18, y - 34 + bob))
            else:
                for i in range(3):
                    gfx.blit_center(surf, self._sprite("cheese", i * 120), (x - 14 + i * 14, y - 26 + bob), scale=0.7)

    def _draw_hint(self, surf):
        """Nothing happened for a while: a see-through hand acts out the next step."""
        t = self.t
        sx, sy = self.station
        cx, cy = self.center
        if self.item:
            tool = TOOL.get(self.item["kind"], "knife")
            if tool == "blender":                               # runs by itself, nothing to show
                return
            if tool == "knife":                                 # come to the knife and just hold it there
                x, y = self._cut_point()
                u = (t * 0.6) % 1.0
                k = ease_out_cubic(min(1.0, u / 0.4))
                ghost_hand(surf, (x + 120 * (1 - k), y - 30 - 70 * (1 - k)), t, scale=1 + 0.06 * math.sin(t * 5))
            else:                                               # rub up and down
                ghost_hand(surf, (sx + 40, sy - 30 + 60 * math.sin(t * 7)), t,
                           holding=whole_sprite(self.item["kind"], 34))
            return
        if self.bowl and self.bowl["left"] > 0:
            mode = self.bowl["mode"]
            what = ladle_sprite() if mode == "sauce" else self._sprite(self.bowl["kind"], 0)
            if self.carry:                                      # with a piece: hold still on the pizza
                ghost_hand(surf, (cx + 40, cy - 20), t, scale=1 + 0.08 * math.sin(t * 5))
                return
            u = (t * 0.5) % 1.0                                 # bowl -> pizza, then a pause
            k = ease_out_cubic(min(1.0, u / 0.6))
            ghost_hand(surf, (sx + (cx - sx) * k, sy + (cy - sy) * k), t, holding=what if k > 0.05 else None)
            return
        if self.toppings or self.sauce_dabs:                    # done? -> the oven button
            ghost_hand(surf, (self.oven.c[0] - 10, self.oven.c[1] + 30), t, scale=1 + 0.1 * math.sin(t * 5))
            return
        b = self.bins[int(t / 1.6) % len(self.bins)]            # nothing yet: point at the ingredients in turn
        k = ease_out_cubic(min(1.0, (t % 1.6) / 0.7))
        ghost_hand(surf, (cx + (b.c[0] - cx) * k, cy + (b.c[1] - cy) * k), t)

    def _draw_work(self, surf, hands):
        """The ingredient on its way: cut on the board, blended in a bowl, or grated. The knife
        and the cheese lie there (glowing) until a hand takes them, then they move with it."""
        sx, sy = self.station
        kind, work = self.item["kind"], self.item["work"]
        tool = TOOL.get(kind, "knife")
        k_in = max(0.05, ease_out_back(min(1.0, self.item["t"] / 0.35)))
        frac = work / WORK[tool]
        held = hands.get(self.tool_hand) if self.tool_hand else None
        rest = self._tool_rest(tool)
        if held is None and tool != "blender":                      # "take me": the tool glows
            gfx.add_glow(surf, rest, 70 + 8 * math.sin(self.t * 6), (255, 230, 140), 0.7)
        spr = whole_sprite(kind)
        if tool == "knife":
            # every cut takes one slice off the right end: the rest gets shorter, the slices
            # lie in a row next to it
            gfx.blit_center(surf, board_sprite(), (sx, sy + 10))
            w, h = spr.get_size()
            left = sx - 110
            remain = self._cut_right() - left
            if work == 0:
                gfx.blit_center(surf, spr, (left + w / 2, sy), scale=k_in)
            else:
                surf.blit(spr.subsurface((0, 0, int(remain), h)), (left, sy - h / 2))
            for i in range(work):                               # the slices cut so far
                gfx.blit_center(surf, self._sprite(kind, 0), (left + remain + 26 + i * 30, sy + 4 - (i % 2) * 6),
                                scale=0.7)
            if held:                                            # the knife in the hand, blade down;
                sink = 22 * min(1.0, self.item.get("hover", 0.0) / HOVER_CUT[self.ctx.level])   # held still: it sinks in
                gfx.blit_center(surf, tool_sprite("knife"), (held[0] - 8, held[1] + 30 + sink), angle=70)
            else:                                               # waiting right over the next cut
                gfx.blit_center(surf, tool_sprite("knife"), (rest[0], rest[1] + 6 * math.sin(self.t * 4)), angle=70)
        elif tool == "blender":                                 # tomatoes whirl round in the bowl, sauce rises
            gfx.blit_center(surf, bowl_sprite(), (sx, sy + 8))
            if work:                                            # the sauce in the bowl gets more
                rw, rh = 120 * (0.4 + 0.6 * frac), 30 * (0.4 + 0.6 * frac)
                pygame.draw.ellipse(surf, (205, 45, 35), (sx - rw / 2, sy - 12 - rh / 2, rw, rh))
                pygame.draw.ellipse(surf, (230, 85, 65), (sx - rw / 4, sy - 16 - rh / 4, rw / 3, rh / 3))
            spin = self.item.get("spin", 0.0)
            for i in range(2):                                  # the tomatoes go round and shrink
                a = spin + i * math.pi
                gfx.blit_center(surf, whole_sprite(kind, 30),
                                (sx + math.cos(a) * 30, sy - 10 + math.sin(a) * 8), scale=max(0.05, k_in * (1 - 0.85 * frac)))
            shake = math.sin(self.t * 60) * 3                   # the blender rattles while it runs
            gfx.blit_center(surf, tool_sprite("blender"), (sx + 20 + shake, sy - 46), angle=shake * 2)
        else:                                                   # cheese rubbed over the grater
            gfx.blit_center(surf, board_sprite(), (sx, sy + 10))
            gfx.blit_center(surf, tool_sprite("grater"), (sx + 40, sy - 4))
            for i in range(work * 2):                           # the grated pile grows
                gfx.blit_center(surf, self._sprite("cheese", i * 50 % 360), (sx + 5 + (i % 4) * 22, sy + 30), scale=0.6)
            # the piece of cheese: in the hand (rub it up and down) or lying next to the grater
            gfx.blit_center(surf, whole_sprite(kind, 34), held if held else rest, scale=k_in * (1 - 0.5 * frac))

    def result_draw(self, surf):
        """Your baked pizza (one slice eaten) and the happy customer."""
        k = ease_out_back(self.state_t / 0.7)
        if getattr(self, "_result_pie", None) is None:
            self._result_pie = self._pie_surface(1.0, 1, 4)
        gfx.blit_center(surf, self._result_pie, (self.W * 0.38, self.H * 0.52), scale=max(0.05, 0.85 * k))
        gfx.blit_center(surf, eater_sprite(0.0, happy=True), (self.W * 0.66, self.H * 0.52), scale=max(0.05, 0.9 * k))
        for i in range(4):                                  # little hearts above the customer
            a = self.state_t * 2 + i * 1.6
            gfx.blit_center(surf, heart_sprite(), (self.W * 0.66 + math.cos(a) * 100, self.H * 0.22 + math.sin(a * 1.3) * 14),
                            scale=max(0.05, 0.8 * k))
