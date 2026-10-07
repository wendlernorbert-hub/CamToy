"""Gemeinsame Bausteine: Schrift, Klänge, Sprache, Partikel, Buttons, Spiel-Grundklasse."""
import colorsys
import math
import os
import queue
import random
import threading

import numpy as np
import pygame

# ------------------------------------------------------------------ Schrift ---
_fonts = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("segoeui,arial,dejavusans,freesans", size, bold=bold)
    return _fonts[key]


def text(surf, s, size, pos, color=(255, 255, 255), anchor="center", shadow=True):
    f = font(size)
    img = f.render(s, True, color)
    r = img.get_rect(**{anchor: pos})
    if shadow:
        surf.blit(f.render(s, True, (25, 25, 60)), r.move(2, 3))
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

def circle_alpha(surf, color, center, radius, width=0):
    radius = max(1, int(radius))
    tmp = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(tmp, color, (radius + 2, radius + 2), radius, width)
    surf.blit(tmp, (int(center[0]) - radius - 2, int(center[1]) - radius - 2))


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
    n = max(3, int(64 * frac))
    outer, inner = [], []
    for i in range(n + 1):
        a = start + 2 * math.pi * frac * i / n
        outer.append((center[0] + math.cos(a) * r_out, center[1] + math.sin(a) * r_out))
        inner.append((center[0] + math.cos(a) * r_in, center[1] + math.sin(a) * r_in))
    pygame.draw.polygon(surf, color, outer + inner[::-1])


def draw_stars_row(surf, center, total, filled, size, t=0.0, spacing=1.25):
    x0 = center[0] - (total - 1) * size * spacing / 2
    for i in range(total):
        c = (x0 + i * size * spacing, center[1])
        if i < filled:
            draw_star(surf, c, size * 0.55, (255, 214, 40), outline=(190, 120, 0))
        else:
            draw_star(surf, c, size * 0.5, (150, 165, 215), outline=(255, 255, 255))


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
                pygame.draw.circle(surf, col, (int(x), int(y)), int(s))
            elif shape == "star":
                draw_star(surf, (x, y), s * 1.3, col, rot)
            else:
                w, h = s * 1.4, s * 0.8
                c, sn = math.cos(rot), math.sin(rot)
                pts = [(x + px * c - py * sn, y + px * sn + py * c)
                       for px, py in ((-w, -h), (w, -h), (w, h), (-w, h))]
                pygame.draw.polygon(surf, col, pts)


# ------------------------------------------------------------------ Klänge ---
SR = 22050


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


class Sounds:
    def __init__(self, enabled=True):
        self.s = {}
        self.enabled = False
        if not enabled:
            return
        try:
            pygame.mixer.init(SR, -16, 2, 512)
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
        }
        for k, v in defs.items():
            v = np.clip(v, -1, 1)
            st = np.ascontiguousarray(np.column_stack([v, v]) * 32000).astype(np.int16)
            self.s[k] = pygame.sndarray.make_sound(st)

    def play(self, name):
        if self.enabled and name in self.s:
            self.s[name].play()


class Speaker:
    """Sprachausgabe (offline, pyttsx3). Fehlt sie, bleibt alles stumm."""

    def __init__(self, enabled=True):
        self.q = queue.Queue()
        self.on = False
        if enabled:
            threading.Thread(target=self._run, daemon=True).start()

    def say(self, s):
        if not self.on:
            return
        try:
            while True:
                self.q.get_nowait()
        except queue.Empty:
            pass
        self.q.put(s)

    def _run(self):
        try:
            if os.name == "nt":                      # COM pro Thread (Windows-Sprachausgabe)
                import ctypes
                ctypes.windll.ole32.CoInitialize(None)
            import pyttsx3
            eng = pyttsx3.init()
            for v in eng.getProperty("voices"):
                blob = (str(v.id) + " " + str(v.name)).lower()
                if any(k in blob for k in ("de-de", "de_de", "german", "deutsch")):
                    eng.setProperty("voice", v.id)
                    break
            eng.setProperty("rate", 150)
        except Exception as e:  # noqa: BLE001
            print("Sprachausgabe aus:", e)
            return
        self.on = True
        while True:
            s = self.q.get()
            try:
                eng.say(s)
                eng.runAndWait()
            except Exception:  # noqa: BLE001
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

    def draw(self, surf, t=0.0):
        r = int(self.r * (1.07 if self.hover else 1.0))
        circle_alpha(surf, (255, 255, 255, 150 if self.hover else 95), self.c, r)
        pygame.draw.circle(surf, self.color, self.c, r, 5)
        if self.icon:
            self.icon(surf, self.c, int(r * 0.62))
        draw_ring(surf, self.c, r + 14, r + 5, self.progress, (255, 225, 60))


def draw_cursors(surf, pose, t):
    """Leuchtende Punkte an den Händen - so sieht das Kind, was es steuert."""
    if not pose:
        return
    for s, col in (("l", (255, 120, 200)), ("r", (90, 220, 255))):
        for part in ("idx", "wr"):
            n = f"{s}_{part}"
            if pose.vis(n) >= 0.35:
                x, y = float(pose.P(n)[0]), float(pose.P(n)[1])
                circle_alpha(surf, col + (70,), (x, y), 30 + 3 * math.sin(t * 8))
                circle_alpha(surf, col + (150,), (x, y), 17)
                pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), 7)
                break


# ------------------------------------------------------------ Spiel-Basis ---

class Ctx:
    def __init__(self, W, H, sounds, speaker, tracker, out_dir):
        self.W, self.H = W, H
        self.sounds, self.speaker, self.tracker = sounds, speaker, tracker
        self.out_dir = out_dir
        self.level = 1          # 1 = leicht (3-4 J.), 2 = mittel, 3 = schwer (6+ J.)
        self.debug = False
        self.has_mask = False

    def play(self, name):
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

    @staticmethod
    def icon(surf, c, r):
        pass

    def __init__(self, ctx):
        self.ctx, self.W, self.H = ctx, ctx.W, ctx.H
        self.particles = Particles()
        self.t = 0.0
        self.exit = False
        self.home = DwellButton((58, 58), 40, 1.2, icon_home)
        self.btn_again = DwellButton((self.W / 2 - 120, self.H * 0.83), 56, 1.0, icon_replay)
        self.btn_home = DwellButton((self.W / 2 + 120, self.H * 0.83), 56, 1.0, icon_home)
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
        self.particles.confetti(self.W)
        self.ctx.play("cheer")
        self.ctx.say("Super gemacht!")

    def update(self, dt, pose):
        self.t += dt
        self.state_t += dt
        self.particles.update(dt)
        hands = pose.hand_points() if pose else []
        if self.home.update(dt, hands):
            self.ctx.play("click")
            self.exit = True
        if self.state == "intro":
            if self.state_t >= self.intro_time:
                self.state, self.state_t = "play", 0.0
                self.on_play_start()
        elif self.state == "play":
            self.play_update(dt, pose, hands)
        else:
            if self.btn_again.update(dt, hands):
                self.ctx.play("click")
                self.restart()
            if self.btn_home.update(dt, hands):
                self.exit = True

    def draw(self, surf, pose):
        if self.state == "intro":
            self.play_draw(surf, pose)
            veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            veil.fill((20, 20, 60, 120))
            surf.blit(veil, (0, 0))
            k = ease_out_back(self.state_t / 0.5)
            self.icon(surf, (self.W // 2, self.H // 2 - 20), int(150 * k))
            text(surf, self.title, 64, (self.W // 2, self.H // 2 + 190))
        elif self.state == "play":
            self.play_draw(surf, pose)
        if self.state == "result":
            veil = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            veil.fill((20, 20, 60, 140))
            surf.blit(veil, (0, 0))
            self.result_draw(surf)
            filled = min(self.stars, int(self.state_t / 0.45))
            draw_stars_row(surf, (self.W // 2, self.H * 0.2), 5, filled, 78, self.t)
            self.btn_again.draw(surf, self.t)
            self.btn_home.draw(surf, self.t)
        self.particles.draw(surf)
        self.home.draw(surf, self.t)
        if self.state != "intro":
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
