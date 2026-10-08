"""Pose-Hilfen: Landmark-Namen, Geometrie, synthetisches Skelett.

Das synthetische Skelett (make_skeleton) dient dreifach:
  * als Trainer-Figur, die die Posen vormacht,
  * als Maus-Modus ohne Kamera,
  * für die automatischen Tests.
"""
import math
import numpy as np

# MediaPipe-Pose-Indizes. "l_" = linke Körperseite des Spielers = linke Bildseite
# (Spiegelbild), "r_" = rechts.
LM = dict(nose=0, l_eye=2, r_eye=5, l_ear=7, r_ear=8, mouth_l=9, mouth_r=10,
          l_sh=11, r_sh=12, l_el=13, r_el=14, l_wr=15, r_wr=16,
          l_idx=19, r_idx=20, l_hip=23, r_hip=24, l_kn=25, r_kn=26,
          l_an=27, r_an=28)

BONES = [("l_sh", "r_sh"), ("l_sh", "l_el"), ("l_el", "l_wr"),
         ("r_sh", "r_el"), ("r_el", "r_wr"), ("l_sh", "l_hip"),
         ("r_sh", "r_hip"), ("l_hip", "r_hip"), ("l_hip", "l_kn"),
         ("l_kn", "l_an"), ("r_hip", "r_kn"), ("r_kn", "r_an")]


class Pose:
    """Landmarks (33x3: x, y normiert 0..1, Sichtbarkeit) plus Pixel-Geometrie."""

    def __init__(self, lm, w, h, slot=0):
        self.lm = lm
        self.w, self.h = w, h
        self.slot = slot                 # stays the same for a person from frame to frame
        self.all = [self]
        self._px = lm[:, :2].astype(np.float64) * np.array([w, h], dtype=np.float64)

    def vis(self, name):
        return float(self.lm[LM[name], 2])

    def has(self, *names, thr=0.5):
        return all(self.lm[LM[n], 2] >= thr for n in names)

    def P(self, name):
        """Position in Bildschirm-Pixeln (numpy-Vektor)."""
        return self._px[LM[name]]

    def mid(self, a, b):
        return (self._px[LM[a]] + self._px[LM[b]]) / 2

    @property
    def ok(self):
        return self.has("l_sh", "r_sh", thr=0.5)

    def shoulder_w(self):
        return float(np.linalg.norm(self.P("l_sh") - self.P("r_sh")))

    def torso(self):
        if self.has("l_hip", "r_hip", thr=0.4):
            return float(np.linalg.norm(self.mid("l_sh", "r_sh") - self.mid("l_hip", "r_hip")))
        return 1.4 * self.shoulder_w()

    def hand_points(self, thr=0.35):
        """Alle Hand-Punkte (Handgelenk + Zeigefinger) für Berührungen."""
        pts = []
        for s in "lr":
            for part in ("wr", "idx"):
                n = f"{s}_{part}"
                if self.vis(n) >= thr:
                    pts.append(tuple(self.P(n)))
        return pts

    def pointer_points(self, thr=0.35):
        """One point per hand (index finger, else wrist) - for buttons that sit close together."""
        pts = []
        for s in "lr":
            for part in ("idx", "wr"):
                if self.vis(f"{s}_{part}") >= thr:
                    pts.append(tuple(self.P(f"{s}_{part}")))
                    break
        return pts

    def named_hand_points(self, thr=0.35):
        d = {}
        for s in "lr":
            for part in ("wr", "idx"):
                n = f"{s}_{part}"
                if self.vis(n) >= thr:
                    d[n] = tuple(self.P(n))
        return d

    def foot_points(self, thr=0.5):
        d = {}
        for n in ("l_an", "r_an", "l_kn", "r_kn"):
            if self.vis(n) >= thr:
                d[n] = tuple(self.P(n))
        return d

    def head(self):
        """(Mittelpunkt, Breite, Neigungswinkel im Bogenmaß) des Kopfes oder None."""
        if not self.has("nose", "l_eye", "r_eye", thr=0.4):
            return None
        le, re_ = self.P("l_eye"), self.P("r_eye")
        eye_mid = (le + re_) / 2
        d = re_ - le
        tilt = math.atan2(d[1], d[0])
        eye_d = float(np.linalg.norm(d))
        if self.has("l_ear", "r_ear", thr=0.35):
            hs = float(np.linalg.norm(self.P("l_ear") - self.P("r_ear")))
            hs = max(hs, eye_d * 1.9)
        else:
            hs = eye_d * 2.6
        return eye_mid, hs, tilt


class Players:
    """Everyone in view (usually a child on a parent's lap).

    Behaves like the main person's Pose for code that only looks at one body; the hand
    helpers return the hands of everybody, so both people can hit, pop and press buttons.
    `all` lists every Pose (each with its own .slot)."""

    def __init__(self, poses):
        self.all = poses
        # main person: the one whose upper body is seen best, then the bigger one
        self.main = max(poses, key=lambda p: (p.ok, p.shoulder_w() if p.ok else 0.0))

    def __getattr__(self, name):
        return getattr(self.main, name)

    @property
    def ok(self):
        return any(p.ok for p in self.all)

    def hand_points(self, thr=0.35):
        return [pt for p in self.all for pt in p.hand_points(thr)]

    def pointer_points(self, thr=0.35):
        return [pt for p in self.all for pt in p.pointer_points(thr)]

    def named_hand_points(self, thr=0.35):
        d = {}
        for p in self.all:
            for n, v in p.named_hand_points(thr).items():
                d[n if p.slot == 0 else f"{n}#{p.slot}"] = v
        return d


def make_players(people, w, h):
    """people: [(slot, landmarks)] from the tracker -> Players, or None if nobody is there."""
    poses = [Pose(lm, w, h, slot) for slot, lm in people]
    if not poses:
        return None
    return poses[0] if len(poses) == 1 else Players(poses)


# ---------------------------------------------------------------- Skelett ---

SW2, HW2 = 0.11, 0.07            # halbe Schulter-/Hüftbreite
TORSO, HEAD_UP = 0.30, 0.11
UA, FA, TH, SH = 0.17, 0.16, 0.22, 0.22

# [armL_dx, armL_dy, armR_dx, armR_dy, legL_dx, legL_lift, legR_dx, legR_lift, hip_h]
# Arme: Handziel relativ zur Schulter. Beine: Fußziel relativ zur Hüftmitte (dx),
# lift = wie weit der Fuß vom Boden angehoben ist.
STAND = [-0.03, 0.31, 0.03, 0.31, -0.07, 0.0, 0.07, 0.0, 0.43]
PRESETS = {
    "stand": STAND,
    "baum": [0.08, -0.325, -0.08, -0.325, -0.07, 0.0, 0.07, 0.0, 0.43],
    "frosch": [-0.05, 0.31, 0.05, 0.31, -0.16, 0.0, 0.16, 0.0, 0.22],
    "stern": [-0.23, -0.23, 0.23, -0.23, -0.20, 0.0, 0.20, 0.0, 0.39],
    "schmetterling": [-0.32, -0.02, 0.32, -0.02, -0.07, 0.0, 0.07, 0.0, 0.43],
    "hase": [0.05, -0.20, -0.05, -0.20, -0.07, 0.0, 0.07, 0.0, 0.43],
}


def lerp_vec(a, b, t):
    return [x + (y - x) * t for x, y in zip(a, b)]


def _ik(p0, target, l1, l2, prefer):
    d = target - p0
    dist = float(np.hypot(d[0], d[1]))
    dist = min(max(dist, 1e-4), (l1 + l2) * 0.999)
    u = d / max(np.hypot(d[0], d[1]), 1e-6)
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    perp = np.array([-u[1], u[0]])
    if float(np.dot(perp, prefer)) < 0:
        perp = -perp
    return p0 + u * a + perp * h, p0 + u * dist


def make_skeleton(vec=None, cx=0.5, ground=0.97, s=0.80, aspect=4 / 3):
    """Baut ein Skelett (33x3) aus dem Parametervektor. aspect = Breite/Höhe."""
    if vec is None:
        vec = STAND
    alx, aly, arx, ary, llx, lll, rlx, rll, hip_h = vec
    hip = np.array([0.0, ground - hip_h * s])
    sh_mid = hip + np.array([0.0, -TORSO * s])
    f = np.zeros((33, 2), np.float32)       # Figur-Einheiten (x in Höhe-Einheiten)
    f[:] = hip

    def put(name, p):
        f[LM[name]] = p

    for side, name, (dx, dy) in ((-1, "l", (alx, aly)), (1, "r", (arx, ary))):
        sh = sh_mid + np.array([side * SW2 * s, 0.0])
        el, wr = _ik(sh, sh + np.array([dx, dy]) * s, UA * s, FA * s,
                     np.array([side * 0.4, 1.0]))
        fd = wr - el
        fd = fd / max(float(np.hypot(*fd)), 1e-6)
        put(f"{name}_sh", sh)
        put(f"{name}_el", el)
        put(f"{name}_wr", wr)
        put(f"{name}_idx", wr + fd * 0.04 * s)
    for side, name, (dx, lift) in ((-1, "l", (llx, lll)), (1, "r", (rlx, rll))):
        hp = hip + np.array([side * HW2 * s, 0.0])
        tgt = hip + np.array([dx * s, (hip_h - lift) * s])
        kn, an = _ik(hp, tgt, TH * s, SH * s, np.array([side * 1.0, 0.1]))
        put(f"{name}_hip", hp)
        put(f"{name}_kn", kn)
        put(f"{name}_an", an)
    nose = sh_mid + np.array([0.0, -HEAD_UP * s])
    put("nose", nose)
    put("l_eye", nose + np.array([-0.022, -0.022]) * s)
    put("r_eye", nose + np.array([0.022, -0.022]) * s)
    put("l_ear", nose + np.array([-0.052, -0.006]) * s)
    put("r_ear", nose + np.array([0.052, -0.006]) * s)
    put("mouth_l", nose + np.array([-0.016, 0.034]) * s)
    put("mouth_r", nose + np.array([0.016, 0.034]) * s)
    out = np.zeros((33, 3), np.float32)
    out[:, 0] = cx + f[:, 0] / aspect
    out[:, 1] = f[:, 1]
    out[:, 2] = 0.99
    return out


# ------------------------------------------------------------ Zeichnen ---

def draw_figure(surf, lm, rect, aspect=4 / 3, body=(70, 150, 235), skin=(255, 214, 170),
                y0=0.08, y1=0.99):
    """Zeichnet ein niedliches Strichmännchen aus Landmarks in ein Rechteck."""
    import pygame
    scale = rect.h / (y1 - y0)

    def m(name):
        i = LM[name]
        return (rect.centerx + (float(lm[i, 0]) - 0.5) * aspect * scale,
                rect.top + (float(lm[i, 1]) - y0) * scale)

    w = max(6, int(0.036 * 0.8 * scale))
    dark = (30, 40, 70)

    def limb(a, b, col, width):
        pygame.draw.line(surf, col, a, b, width)
        pygame.draw.circle(surf, col, (int(a[0]), int(a[1])), width // 2)
        pygame.draw.circle(surf, col, (int(b[0]), int(b[1])), width // 2)

    chains = [("l_hip", "l_kn", "l_an"), ("r_hip", "r_kn", "r_an"),
              ("l_sh", "l_el", "l_wr"), ("r_sh", "r_el", "r_wr")]
    for outline in (True, False):
        col = dark if outline else body
        ww = w + 6 if outline else w
        for c in chains:
            limb(m(c[0]), m(c[1]), col, ww)
            limb(m(c[1]), m(c[2]), col, ww)
        quad = [m("l_sh"), m("r_sh"), m("r_hip"), m("l_hip")]
        if outline:
            pygame.draw.polygon(surf, dark, quad)
            pygame.draw.lines(surf, dark, True, quad, 6)
        else:
            pygame.draw.polygon(surf, body, quad)
    for n in ("l_wr", "r_wr"):
        p = m(n)
        pygame.draw.circle(surf, dark, (int(p[0]), int(p[1])), w // 2 + 5)
        pygame.draw.circle(surf, skin, (int(p[0]), int(p[1])), w // 2 + 2)
    for n in ("l_an", "r_an"):
        p = m(n)
        pygame.draw.circle(surf, dark, (int(p[0]), int(p[1])), w // 2 + 5)
        pygame.draw.circle(surf, (230, 90, 70), (int(p[0]), int(p[1])), w // 2 + 2)
    # Kopf
    nose, le, re_ = m("nose"), m("l_eye"), m("r_eye")
    el, er = m("l_ear"), m("r_ear")
    r = max(10, int(math.hypot(er[0] - el[0], er[1] - el[1]) * 0.82))
    c = (int((nose[0] + le[0] + re_[0]) / 3), int((nose[1] + le[1] + re_[1]) / 3 - r * 0.05))
    pygame.draw.circle(surf, dark, c, r + 3)
    pygame.draw.circle(surf, skin, c, r)
    for e in (le, re_):
        pygame.draw.circle(surf, dark, (int(e[0]), int(e[1])), max(2, r // 9))
    pygame.draw.arc(surf, (190, 70, 70),
                    (c[0] - r // 2, c[1] - r // 4, r, int(r * 0.8)),
                    math.pi * 1.15, math.pi * 1.85, max(2, r // 10))
