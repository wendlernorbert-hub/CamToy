"""Gemeinsame Bausteine: Schrift, Klänge, Sprache, Partikel, Buttons, Spiel-Grundklasse."""
import colorsys
import math
import os
import random
import sys

import numpy as np
import pygame

import gfx

# ------------------------------------------------------------------ Schrift ---


def font(size, bold=True):
    return gfx.font(size)


def text(surf, s, size, pos, color=(255, 255, 255), anchor="center", shadow=True):
    """Chunky outlined game lettering (cached). Mostly numbers - the players cannot read."""
    img = gfx.label(s, size, color) if shadow else gfx.cached(("plain", s, size, tuple(color)),
                                                              lambda: gfx.font(size).render(s, True, color))
    r = img.get_rect(**{anchor: pos})
    surf.blit(img, r)
    return r


def rainbow(i, n=7, s=0.75, v=1.0):
    r, g, b = colorsys.hsv_to_rgb((i % n) / n, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def ease_out_back(t):
    t = max(0.0, min(1.0, t))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# ---------------------------------------------------------------- Zeichnen ---

_circles = {}
_veils = {}


def circle_alpha(surf, color, center, radius, width=0):
    radius = max(1, int(radius))
    # fading effects can overshoot by one frame (alpha -3): clamp instead of crashing (play-test bug)
    color = tuple(max(0, min(255, int(v))) for v in color)
    if len(color) == 4 and color[3] == 0:
        return
    key = (color, radius, width)
    tmp = _circles.get(key)
    if tmp is None:
        if len(_circles) > 400:
            _circles.clear()
        tmp = _circles[key] = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(tmp, color, (radius + 2, radius + 2), radius, width)
    surf.blit(tmp, (int(center[0]) - radius - 2, int(center[1]) - radius - 2))


def veil(size, rgba):
    """A see-through full-screen tint, made once and reused."""
    key = (tuple(size), tuple(rgba))
    v = _veils.get(key)
    if v is None:
        v = _veils[key] = pygame.Surface(size, pygame.SRCALPHA)
        v.fill(rgba)
    return v


def poly_alpha(surf, color, pts):
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    w, h = int(max(xs) - x0) + 4, int(max(ys) - y0) + 4
    if w < 2 or h < 2 or w > 4000 or h > 4000:
        return
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(tmp, color, [(float(x) - x0, float(y) - y0) for x, y in pts])
    surf.blit(tmp, (x0, y0))


def star_pts(c, r, rot=0.0, inner=0.45, points=5):
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * inner
        a = rot - math.pi / 2 + i * math.pi / points
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    return pts


def draw_star(surf, c, r, color, rot=0.0, outline=None, inner=0.45):
    pts = star_pts(c, r, rot, inner)
    pygame.draw.polygon(surf, color, pts)
    if outline:
        pygame.draw.polygon(surf, outline, pts, max(2, int(r * 0.12)))


def heart_pts(c, r, n=40):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((c[0] + x / 17 * r, c[1] + y / 17 * r))
    return pts


def ellipse_pts(cx, cy, rx, ry, rot=0.0, n=24):
    pts = []
    cr, sr = math.cos(rot), math.sin(rot)
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = math.cos(t) * rx, math.sin(t) * ry
        pts.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
    return pts


def draw_ring(surf, center, r_out, r_in, frac, color, start=-math.pi / 2):
    frac = max(0.0, min(1.0, frac))
    if frac <= 0:
        return
    n = max(3, int(96 * frac))
    outer, inner = [], []
    for i in range(n + 1):
        a = start + 2 * math.pi * frac * i / n
        outer.append((center[0] + math.cos(a) * r_out, center[1] + math.sin(a) * r_out))
        inner.append((center[0] + math.cos(a) * r_in, center[1] + math.sin(a) * r_in))
    pygame.draw.polygon(surf, color, outer + inner[::-1])
    pygame.draw.aalines(surf, color, False, outer)               # smooth edges
    pygame.draw.aalines(surf, color, False, inner)


def progress_ring(surf, center, r, frac, color=(255, 214, 50), width=12):
    """Dwell progress: a dark track, a bright ring with round ends and a glowing tip."""
    if frac <= 0:
        return
    draw_ring(surf, center, r + width / 2 + 3, r - width / 2 - 3, 1.0, (44, 34, 72))
    draw_ring(surf, center, r + width / 2, r - width / 2, frac, color)
    a = -math.pi / 2 + 2 * math.pi * min(1.0, frac)
    for ang in (-math.pi / 2, a):
        p = (center[0] + math.cos(ang) * r, center[1] + math.sin(ang) * r)
        gfx.blit_center(surf, gfx.ball(width / 2 + 1, color), p)
    gfx.add_glow(surf, (center[0] + math.cos(a) * r, center[1] + math.sin(a) * r), width * 2.4, color, 0.9)


def star_sprite(size, color=(255, 214, 40), outline=3):
    """Polished star (puffy, outlined), size = radius in px."""
    size = max(3, int(size))
    return gfx.cached(("star", size, tuple(color), outline), lambda: gfx.icon_sprite(
        lambda s, c, r: draw_star(s, c, r, color, 0, inner=0.5), size, pad=1.1,
        outline=outline, depth=0.3, shadow=70 if size > 12 else 0))


def empty_star_sprite(size):
    size = max(3, int(size))

    def build():
        spr = gfx.icon_sprite(lambda s, c, r: draw_star(s, c, r, (255, 255, 255), 0, inner=0.5),
                              size, pad=1.1, puffy=False, outline=3, shadow=0)
        spr.set_alpha(120)
        return spr
    return gfx.cached(("estar", size), build)


_star_rows = {}


def draw_stars_row(surf, center, total, filled, size, t=0.0, spacing=1.25):
    """Row of star slots; a star that just got filled pops in with a bounce and a flash."""
    now = pygame.time.get_ticks() / 1000
    key = (int(center[0]), int(center[1]), total)
    prev, times = _star_rows.get(key, (filled, {}))
    for i in range(prev, filled):
        times[i] = now
    _star_rows[key] = (filled, times)
    x0 = center[0] - (total - 1) * size * spacing / 2
    for i in range(total):
        c = (x0 + i * size * spacing, center[1])
        if i < filled:
            age = now - times.get(i, -9)
            k = ease_out_back(age / 0.45) if age < 0.45 else 1.0
            if age < 0.4:
                gfx.add_glow(surf, c, size * 1.4 * (1 - age / 0.4) + 4, (255, 220, 120))
            gfx.blit_center(surf, star_sprite(size * 0.6), c, scale=max(0.05, k),
                            angle=(1 - min(1.0, age / 0.45)) * 90)
        else:
            gfx.blit_center(surf, empty_star_sprite(size * 0.5), c)


def draw_timer(surf, center, w, frac, color=(255, 170, 60)):
    """Time left as a glossy pill that shrinks; turns red near the end."""
    h = 22
    frac = max(0.0, min(1.0, frac))
    late = frac < 0.15
    col = (255, 90, 80) if late else color
    x0, y0 = center[0] - w / 2, center[1] - h / 2
    pygame.draw.rect(surf, (44, 34, 72), (x0 - 4, y0 - 4, w + 8, h + 8), border_radius=(h + 8) // 2)
    pygame.draw.rect(surf, (255, 255, 255), (x0, y0, w, h), border_radius=h // 2)
    fw = max(h, w * frac) if frac > 0 else 0
    if fw:
        bar = pygame.Rect(x0, y0, fw, h)
        pygame.draw.rect(surf, gfx.darker(col, 0.15), bar, border_radius=h // 2)
        pygame.draw.rect(surf, col, bar.inflate(-4, -6).move(0, -2), border_radius=h // 2)
        pygame.draw.rect(surf, gfx.lighter(col, 0.55), (x0 + 8, y0 + 4, max(0, fw - 16), 5), border_radius=3)


def draw_hand(surf, c, r):
    """Pictogram of an open hand (no text: the players cannot read yet)."""
    x, y = c
    k = r / 80
    skin = (255, 214, 170)
    for dx, top, hgt in ((-30, -58, 62), (-10, -74, 74), (10, -74, 74), (30, -58, 62)):     # fingers
        rr = pygame.Rect(x + (dx - 10) * k, y + top * k, 20 * k, hgt * k)
        pygame.draw.ellipse(surf, skin, rr)
    th = pygame.Surface((int(26 * k), int(64 * k)), pygame.SRCALPHA)
    pygame.draw.ellipse(th, skin, th.get_rect())
    th = pygame.transform.rotate(th, 40)
    surf.blit(th, th.get_rect(center=(int(x - 36 * k), int(y + 28 * k))))
    pygame.draw.ellipse(surf, skin, (x - 38 * k, y - 14 * k, 76 * k, 78 * k))
    for dx in (-20, 0, 20):                                                    # knuckle lines
        pygame.draw.arc(surf, (230, 170, 130), (x + (dx - 8) * k, y - 22 * k, 16 * k, 14 * k), 3.6, 5.8, max(2, int(3 * k)))


def ghost_hand(surf, pos, t, scale=1.0, holding=None, hold_angle=0.0):
    """A see-through hand that shows the child what to do next - instead of words.
    holding: a sprite in the hand (the knife, a piece ...), so it is clear WHAT to do."""
    def build():
        spr = gfx.icon_sprite(draw_hand, 58, pad=1.4, outline=4, shadow=0).copy()
        spr.set_alpha(215)
        return spr
    gfx.add_glow(surf, pos, 95 * scale, (255, 240, 170), 0.5 + 0.2 * math.sin(t * 6))
    if holding is not None:
        gfx.blit_center(surf, holding, (pos[0] + 12 * scale, pos[1] + 34 * scale), angle=hold_angle)
    gfx.blit_center(surf, gfx.cached(("ghosthand",), build), pos, scale=scale)


def icon_home(surf, c, r):
    x, y = c
    roof = [(x - r, y - r * 0.05), (x, y - r), (x + r, y - r * 0.05)]
    pygame.draw.polygon(surf, (235, 90, 80), roof)
    pygame.draw.rect(surf, (250, 235, 200), (x - r * 0.68, y - r * 0.05, r * 1.36, r * 0.95))
    pygame.draw.rect(surf, (140, 90, 60), (x - r * 0.2, y + r * 0.3, r * 0.4, r * 0.6))


def icon_replay(surf, c, r):
    draw_ring(surf, c, r * 0.9, r * 0.55, 0.78, (60, 200, 120), start=-math.pi * 0.3)
    a = -math.pi * 0.3 + 2 * math.pi * 0.78
    ex, ey = c[0] + math.cos(a) * r * 0.72, c[1] + math.sin(a) * r * 0.72
    tx, ty = -math.sin(a), math.cos(a)
    nx, ny = math.cos(a), math.sin(a)
    pygame.draw.polygon(surf, (60, 200, 120), [
        (ex + tx * r * 0.55, ey + ty * r * 0.55),
        (ex + nx * r * 0.45, ey + ny * r * 0.45),
        (ex - nx * r * 0.45, ey - ny * r * 0.45)])


# ---------------------------------------------------------------- Partikel ---

class Particles:
    def __init__(self):
        self.p = []

    def burst(self, pos, n=24, colors=((255, 255, 255),), speed=320, life=0.8,
              size=(4, 10), gravity=600, shape="circle", up=0.0):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(0.3, 1.0) * speed
            self.p.append([pos[0], pos[1], math.cos(a) * v, math.sin(a) * v - up,
                           life * random.uniform(0.6, 1.1), life, random.choice(colors),
                           random.uniform(*size), shape, gravity, random.uniform(0, 6.28)])

    def confetti(self, W, n=90):
        for _ in range(n):
            self.p.append([random.uniform(0, W), random.uniform(-120, -10),
                           random.uniform(-60, 60), random.uniform(80, 260),
                           random.uniform(2.5, 4.0), 3.0, rainbow(random.randint(0, 6)),
                           random.uniform(6, 11), random.choice(["rect", "star", "circle"]),
                           60, random.uniform(0, 6.28)])

    def update(self, dt):
        for p in self.p:
            p[3] += p[9] * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            p[10] += dt * 6
        self.p = [p for p in self.p if p[4] > 0]

    def draw(self, surf):
        for x, y, _, _, life, maxl, col, size, shape, _, rot in self.p:
            sc = min(1.0, life / (0.35 * maxl)) if maxl > 0 else 1.0
            s = max(1.0, size * sc)
            if shape == "circle":
                gfx.blit_center(surf, gfx.ball(max(2, int(s)), col), (x, y))
            elif shape == "star":
                spr = gfx.cached(("pstar", int(s * 1.3), tuple(col), int(math.degrees(rot) / 15) % 24),
                                 lambda s=s, col=col, rot=rot: pygame.transform.rotozoom(
                                     star_sprite(s * 1.3, col, 2), (int(math.degrees(rot) / 15) % 24) * 15, 1),
                                 fleeting=True)
                surf.blit(spr, spr.get_rect(center=(int(x), int(y))))
            else:
                w, h = s * 1.4, s * 0.8
                c, sn = math.cos(rot), math.sin(rot)
                pts = [(x + px * c - py * sn, y + px * sn + py * c)
                       for px, py in ((-w, -h), (w, -h), (w, h), (-w, h))]
                pygame.draw.polygon(surf, col, pts)


# ------------------------------------------------------------------ Klänge ---
SR = 22050


def _set_rate(rate):
    """Synthesize sounds at the sample rate the (already initialised) mixer runs at."""
    global SR
    SR = int(rate)


def _tone(f0, dur, f1=None, vol=0.5, decay=6.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f1 = f0 if f1 is None else f1
    freq = f0 + (f1 - f0) * t / dur
    x = np.sin(2 * np.pi * np.cumsum(freq) / SR)
    return x * np.exp(-decay * t) * np.minimum(1.0, t * 300) * vol


def _noise(dur, vol=0.5, decay=10.0, smooth=1):
    n = int(SR * dur)
    x = np.random.uniform(-1, 1, n)
    if smooth > 1:
        x = np.convolve(x, np.ones(smooth) / smooth, mode="same")
    return x * np.exp(-decay * np.arange(n) / SR) * vol


def _seq(parts, gap=0.0):
    out = []
    for p in parts:
        out.append(p)
        if gap:
            out.append(np.zeros(int(SR * gap)))
    return np.concatenate(out)


def _mix(*arrs):
    n = max(len(a) for a in arrs)
    out = np.zeros(n)
    for a in arrs:
        out[:len(a)] += a
    return out


POP_PITCHES = 8                              # "pop0" (high, tiny bubble) .. "pop7" (deep, big bubble)


def _plop(f, vol=0.75):
    """Bubble pop: a soft, round 'bloop' - a pure tone that slides up while it fades.
    No click at the start (play-test: that sounded hard and cracking)."""
    dur = 0.07 + 22.0 / f                       # deep pops ring a little longer
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = f * (1 + 0.6 * (1 - np.exp(-t * 35)))
    env = np.minimum(1.0, t / 0.004) * np.exp(-t * (18 + f / 60))       # soft start, round fade
    ph = 2 * np.pi * np.cumsum(freq) / SR
    return (np.sin(ph) + 0.15 * np.sin(2 * ph)) * env * vol


def _blend_whir(dur=1.6, vol=0.5):
    """Hand blender running: a buzzing motor that speeds up, with a wet, bubbly rumble."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 90 + 70 * np.minimum(1, t / 0.3)                          # motor spins up
    motor = 2 * ((np.cumsum(f) / SR) % 1) - 1
    motor = np.convolve(motor, np.ones(6) / 6, mode="same")       # soften the buzz
    slosh = np.convolve(np.random.uniform(-1, 1, n), np.ones(40) / 40, mode="same") * 5
    slosh *= 0.6 + 0.4 * np.sin(2 * np.pi * 7 * t)                # bubbling
    env = np.minimum(1, t / 0.08) * np.minimum(1, (dur - t) / 0.2)
    return (motor * 0.6 + slosh * 0.5) * env * vol


class Sounds:
    def __init__(self, enabled=True):
        self.s = {}
        self.enabled = False
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            _set_rate(pygame.mixer.get_init()[0])   # the mixer is shared with the main game
            pygame.mixer.set_num_channels(32)       # default 8: hits/pops got swallowed in busy moments
        except pygame.error as e:
            print("Kein Ton:", e)
            return
        self.enabled = True
        note = lambda f, d=0.12, v=0.4: _tone(f, d, vol=v, decay=7)  # noqa: E731
        defs = {
            "pop": _mix(_tone(750, 0.13, 260, 0.6, 24), _noise(0.05, 0.25, 60)),
            "gold": _seq([note(f, 0.09) for f in (880, 1100, 1320, 1760)]),
            "chime": _seq([note(f) for f in (523, 659, 784)]),
            "cheer": _seq([note(f, 0.1) for f in (523, 659, 784, 1047, 1319)]
                          + [_tone(1568, 0.5, vol=0.4, decay=4)]),
            "hit": _mix(_noise(0.14, 0.7, 28, 6), _tone(190, 0.2, 60, 0.7, 16)),
            "whoosh": _noise(0.22, 0.35, 9, 40) * np.hanning(int(SR * 0.22)),
            "tick": _tone(1200, 0.05, vol=0.4, decay=60),
            "click": _tone(800, 0.05, 1000, 0.35, 70),
            "poof": _mix(_noise(0.2, 0.35, 14, 12), _tone(400, 0.15, 900, 0.25, 14)),
            "boing": _tone(220, 0.28, 520, 0.5, 8),
            "shutter": _seq([_noise(0.04, 0.6, 80), np.zeros(int(SR * 0.05)),
                             _noise(0.07, 0.5, 60)]),
            "down": _tone(520, 0.22, 260, 0.35, 9),
            "good": _seq([note(660, 0.1), note(880, 0.2)]),
            "board": _mix(_noise(0.18, 0.7, 20, 3), _tone(120, 0.25, 50, 0.7, 12)),
            "blend": _blend_whir(),
        }
        for i in range(POP_PITCHES):            # from ~340 Hz (tiny) down to ~190 Hz (big): deep, soft bloops
            defs[f"pop{i}"] = _plop(340 * (190 / 340) ** (i / (POP_PITCHES - 1)))
        defs["pop_tiny"] = _plop(520, 0.6)          # the rare tiny bubbles: extra high
        defs["pop_giant"] = _plop(120, 0.9)         # the rare giants: extra deep (and longer)
        for k, v in defs.items():
            v = np.clip(v, -1, 1)
            st = np.ascontiguousarray(np.column_stack([v, v]) * 32000).astype(np.int16)
            self.s[k] = pygame.sndarray.make_sound(st)
        # recorded sounds replace the made-up ones; several files = a random one each time
        self.variants = {}
        for name, files in SFX_FILES.items():
            loaded = [snd for snd in (_load_normalized(os.path.join(SFX_DIR, f)) for f in files) if snd]
            if loaded:
                self.variants[name] = loaded

    def play(self, name):
        if not self.enabled:
            return
        if name in self.variants:
            random.choice(self.variants[name]).play()
        elif name in self.s:
            self.s[name].play()
        elif name in SFX_FALLBACK:
            self.play(SFX_FALLBACK[name])


SFX_DIR = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                       "assets", "sfx")


def _own(path):
    """Optional sound the user can record and drop in (any of .wav / .ogg / .mp3)."""
    return [path + ext for ext in (".wav", ".ogg", ".mp3")]


# pizza: knife / grater from Kenney "RPG Audio" (CC0), bites from "7 Eating Crunches" by StarNinjas (CC0)
# voices (frog "quak", "omnomnom", "mmmh") are own recordings, if present - made-up ones sounded odd
SFX_FILES = {"quak": _own("frog/quak"), "omnom": _own("pizza/omnom"), "mmh": _own("pizza/mmh"),
             "cut": ["pizza/chop.ogg", "pizza/knifeSlice.ogg", "pizza/knifeSlice2.ogg"],
             "grate": ["pizza/drawKnife1.ogg", "pizza/drawKnife2.ogg", "pizza/drawKnife3.ogg"],
             "bite": [f"pizza/crunch{i}.ogg" for i in range(1, 8)],
             # mashing tomatoes: "Squish Sounds Effects" by EZduzziteh (CC0)
             "squish": [f"pizza/squish_0{i}.mp3" for i in range(1, 7)]}
# without an own recording: the frog gets the friendly "well done" sound, the voices stay silent
SFX_FALLBACK = {"quak": "good"}


def _load_normalized(path, peak=0.8):
    """Load a sound file and bring it to a normal loudness (some recordings are very quiet)."""
    try:
        snd = pygame.mixer.Sound(path)
    except (pygame.error, FileNotFoundError):
        return None
    a = pygame.sndarray.array(snd).astype(np.float32)
    top = float(np.abs(a).max())
    if top <= 0:
        return None
    a = a * (peak * 32767 / top)
    return pygame.sndarray.make_sound(np.ascontiguousarray(a).astype(np.int16))


class Speaker:
    """Speech output was removed on purpose; the games still call say(), which does nothing."""

    def __init__(self, enabled=False):
        pass

    def say(self, s):
        pass


# ------------------------------------------------------------------ Buttons ---

class DwellButton:
    """Wird ausgelöst, wenn eine Hand ihn lange genug berührt (Fortschrittsring)."""

    def __init__(self, center, radius, dwell=1.0, icon=None, color=(255, 255, 255)):
        self.c, self.r, self.dwell = center, radius, dwell
        self.icon, self.color = icon, color
        self.progress, self.hover, self.armed = 0.0, False, True

    def update(self, dt, pts):
        cx, cy = self.c
        self.hover = any((x - cx) ** 2 + (y - cy) ** 2 <= (self.r * 1.1) ** 2 for x, y in pts)
        if not self.hover:
            self.armed = True
            self.progress = max(0.0, self.progress - dt * 2)
            return False
        if not self.armed:
            return False
        self.progress += dt / self.dwell
        if self.progress >= 1.0:
            self.progress, self.armed = 0.0, False
            return True
        return False

    def draw(self, surf, t=0.0, base=(250, 250, 255)):
        draw_button(surf, self.c, self.r, self.icon, self.color if self.color != (255, 255, 255) else (120, 150, 255),
                    self.hover, self.progress, t, base)


def update_exclusive(buttons, dt, pts, active):
    """A group of dwell buttons where only ONE fills at a time (the one already filling, else
    the touched one nearest to a hand) - so one hand can never pick two things.
    pts: one point per hand (Pose.pointer_points, the same point the cursor ball shows).
    Returns (index of the button that fired or None, new active index)."""
    def dist(i):
        b = buttons[i]
        return min(math.hypot(x - b.c[0], y - b.c[1]) for x, y in pts)
    touched = [i for i, b in enumerate(buttons)
               if any((x - b.c[0]) ** 2 + (y - b.c[1]) ** 2 <= (b.r * 1.1) ** 2 for x, y in pts)]
    if active not in touched:
        active = min(touched, key=dist) if touched else None
    fired = None
    for i, b in enumerate(buttons):
        if i == active:
            if b.update(dt, pts):
                fired = i
        else:                                   # others: just show hover and let them empty
            b.hover = i in touched
            if not b.hover:
                b.armed = True
            b.progress = max(0.0, b.progress - dt * 2)
    return fired, active


def button_sprite(r, rim, base=(250, 250, 255)):
    """Round glossy button body: shiny disc with a coloured rim, outline and shadow."""
    r = int(r)
    return gfx.cached(("button", r, tuple(rim), tuple(base)),
                      lambda: gfx.sticker(gfx.ball(r, base, rim=rim), 4, gfx.INK, shadow=90, offset=(0, 6)))


def icon_of(icon, r):
    """Cached polished sprite of a pictogram function icon(surf, centre, radius)."""
    r = max(4, int(r))
    return gfx.cached(("icon", icon, r), lambda: gfx.icon_sprite(icon, r, pad=1.45, outline=3, shadow=0))


def draw_button(surf, c, r, icon, rim, hover, progress, t, base=(250, 250, 255)):
    k = 1.0 + (0.08 if hover else 0.0) + 0.06 * progress + (0.02 * math.sin(t * 10) if hover else 0)
    if hover:
        gfx.add_glow(surf, c, r * 1.9, gfx.lighter(rim, 0.3), 0.55)
    gfx.blit_center(surf, button_sprite(r, rim, base), c, scale=k)
    if icon:
        gfx.blit_center(surf, icon_of(icon, r * 0.6), c, scale=k)
    progress_ring(surf, c, r * k + 16, progress)


_trails = {}


def draw_cursors(surf, pose, t):
    """Leuchtende Punkte an den Händen des Spielers - so sieht das Kind, was es steuert."""
    if not pose:
        return
    now = pygame.time.get_ticks() / 1000
    for p in pose.all:
        for s, col in (("l", (255, 110, 200)), ("r", (80, 210, 255))):
            key = (p.slot, s)
            trail = _trails.setdefault(key, [])
            for part in ("idx", "wr"):
                n = f"{s}_{part}"
                if p.vis(n) >= 0.35:
                    x, y = float(p.P(n)[0]), float(p.P(n)[1])
                    trail.append((now, x, y))
                    break
            trail[:] = [e for e in trail if now - e[0] < 0.22]
            for i, (tt, x, y) in enumerate(trail[:-1]):          # comet tail
                k = 1 - (now - tt) / 0.22
                gfx.add_glow(surf, (x, y), 10 + 16 * k, col, 0.5 * k)
            if trail and now - trail[-1][0] < 0.05:
                _, x, y = trail[-1]
                gfx.add_glow(surf, (x, y), 46 + 4 * math.sin(t * 8), col, 0.9)
                gfx.blit_center(surf, gfx.ball(13, gfx.lighter(col, 0.45)), (x, y))


# ------------------------------------------------------------ Spiel-Basis ---

class Ctx:
    def __init__(self, W, H, sounds, speaker, tracker, out_dir):
        self.W, self.H = W, H
        self.sounds, self.speaker, self.tracker = sounds, speaker, tracker
        self.out_dir = out_dir
        self.level = 1          # 1 = leicht (3-4 J.), 2 = mittel, 3 = schwer (6+ J.)
        self.debug = False
        self.has_mask = False
        self.log = lambda kind, **kw: None    # play-test recorder (telemetry.Telemetry.event)

    def play(self, name):
        self.log("sfx", name=name)
        self.sounds.play(name)

    def say(self, s):
        self.speaker.say(s)


class Game:
    """Ablauf: intro -> play -> result (bei rounds=False nur play)."""
    title = "Spiel"
    needs_mask = False
    rounds = True
    intro_time = 2.6
    speech = ""
    # button spots as screen fractions; a game that shows the player small (car) moves them
    # to where the hands can actually reach
    home_at = None
    again_at = None
    theme = (120, 150, 255)          # rim colour of this game's buttons
    show_stars = True                # star rating on the result screen

    @staticmethod
    def icon(surf, c, r):
        pass

    def __init__(self, ctx):
        self.ctx, self.W, self.H = ctx, ctx.W, ctx.H
        self.particles = Particles()
        self.t = 0.0
        self.exit = False
        # the home button is top left; "play again" appears top right on the result screen
        # (a bit away from the corner, so it is easy to reach)
        home = (self.home_at[0] * self.W, self.home_at[1] * self.H) if self.home_at else (62, 62)
        again = (self.again_at[0] * self.W, self.again_at[1] * self.H) if self.again_at else (self.W - 150, 100)
        self.home = DwellButton(home, 40, 1.2, icon_home, color=(255, 140, 90))
        self.btn_again = DwellButton(again, 56, 1.0, icon_replay, color=(90, 210, 120))
        self.restart()

    # ---- Ablauf ----
    def restart(self):
        self.state = "intro" if self.rounds else "play"
        self.state_t = 0.0
        self.stars = 0
        self.on_restart()
        if self.speech:
            self.ctx.say(self.speech)

    def finish(self, stars):
        self.state, self.state_t, self.stars = "result", 0.0, max(1, min(5, stars))
        self.ctx.log("result", game=type(self).__name__, level=self.ctx.level, stars=self.stars,
                     score=getattr(self, "score", getattr(self, "coins", "-")))
        self.particles.confetti(self.W, 55)
        self.ctx.play("cheer")
        self.ctx.say("Super gemacht!")

    def update(self, dt, pose):
        self.t += dt
        self.state_t += dt
        self.particles.update(dt)
        hands = pose.hand_points() if pose else []
        pointers = pose.pointer_points() if pose else []      # buttons: the point the cursor shows
        if self.home.update(dt, pointers):
            self.ctx.play("click")
            self.exit = True
        if self.state == "intro":
            if self.state_t >= self.intro_time:
                self.state, self.state_t = "play", 0.0
                self.on_play_start()
        elif self.state == "play":
            self.play_update(dt, pose, hands)
        else:
            if self.btn_again.update(dt, pointers):
                self.ctx.play("click")
                self.restart()

    def draw(self, surf, pose):
        c = (self.W // 2, self.H // 2 - 20)
        if self.state == "intro":
            self.play_draw(surf, pose)
            surf.blit(veil((self.W, self.H), (20, 20, 60, 120)), (0, 0))
            k = ease_out_back(self.state_t / 0.5)
            out = max(0.0, (self.state_t - (self.intro_time - 0.3)) / 0.3)      # zoom away at the end
            gfx.blit_center(surf, gfx.sunburst(330), c, scale=k * (1 + out), angle=self.t * 20)
            gfx.blit_center(surf, icon_of(self.icon, 150), c, scale=max(0.01, k * (1 - out)),
                            sy=1 + 0.04 * math.sin(self.t * 5))
        elif self.state == "play":
            self.play_draw(surf, pose)
        if self.state == "result":
            surf.blit(veil((self.W, self.H), (20, 20, 60, 140)), (0, 0))
            gfx.blit_center(surf, gfx.sunburst(360), (self.W // 2, self.H * 0.42),
                            scale=ease_out_back(self.state_t / 0.6), angle=self.t * 12)
            self.result_draw(surf)
            if self.show_stars:
                filled = min(self.stars, int(max(0.0, self.state_t - 0.3) / 0.4))
                if filled > getattr(self, "_shown_stars", 0):
                    self.ctx.play("gold" if filled == self.stars else "chime")
                self._shown_stars = filled if self.state_t > 0 else 0
                draw_stars_row(surf, (self.W // 2, self.H * 0.17), 5, filled, 96, self.t)
            self.btn_again.draw(surf, self.t)
        else:
            self._shown_stars = 0
        self.particles.draw(surf)
        self.home.draw(surf, self.t)
        if self.state != "intro":
            self.draw_hands(surf, pose)

    def draw_hands(self, surf, pose):
        draw_cursors(surf, pose, self.t)

    # ---- von Spielen zu überschreiben ----
    def on_restart(self):
        pass

    def on_play_start(self):
        pass

    def play_update(self, dt, pose, hands):
        pass

    def play_draw(self, surf, pose):
        pass

    def draw_back(self, surf, pose):
        pass

    def result_draw(self, surf):
        pass

    def on_exit(self):
        pass
