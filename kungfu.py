import glob
import math
import os
import random
import pygame
import numpy as np

import theme

DISPLAY_W = 1280
DISPLAY_H = 720
CAPTURE_W = 640
CAPTURE_H = 480

_SX = CAPTURE_W / DISPLAY_W
_SY = CAPTURE_H / DISPLAY_H

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

_BASE_SPEED    = 140.0   # px/s at difficulty 1
_SPAWN_RATE    = 1.8     # seconds between spawns at difficulty 1
_MIN_SPAWN     = 0.45
_COMBO_TIMEOUT = 1.5     # seconds until combo resets

_SPLASH_COLORS = [theme.INK, theme.VERMILION, theme.VERMILION, theme.VERMILION_DARK]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _star_polygon(cx: float, cy: float, r: float, angle: float, points: int = 6):
    verts = []
    for i in range(points * 2):
        a = math.radians(angle + i * 180 / points)
        rad = r if i % 2 == 0 else r * 0.42
        verts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
    return verts


# ---------------------------------------------------------------------------
# Sounds (synthesized, no asset files)
# ---------------------------------------------------------------------------

_RATE = 44100


def _make_sound(samples: np.ndarray, volume: float = 0.5) -> pygame.mixer.Sound:
    pcm = np.clip(samples, -1.0, 1.0) * 32767 * volume
    stereo = np.ascontiguousarray(np.column_stack([pcm, pcm]).astype(np.int16))
    return pygame.mixer.Sound(buffer=stereo.tobytes())


def _tone(f0: float, f1: float, dur: float, noise: float = 0.0,
          square: bool = False) -> np.ndarray:
    n     = int(_RATE * dur)
    t     = np.arange(n) / _RATE
    freq  = np.linspace(f0, f1, n)
    phase = 2 * np.pi * np.cumsum(freq) / _RATE
    wave  = np.sign(np.sin(phase)) if square else np.sin(phase)
    if noise:
        wave = wave * (1 - noise) + np.random.uniform(-1, 1, n) * noise
    return wave * np.exp(-t * (5.0 / dur))


class Sounds:
    def __init__(self) -> None:
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(_RATE, -16, 2, 512)
            self.hit      = [_make_sound(_tone(600 * 1.12 ** i, 200 * 1.12 ** i,
                                               0.18, noise=0.5), 0.5)
                             for i in range(5)]
            self.star     = _make_sound(_tone(1400, 2200, 0.12, square=True), 0.3)
            self.spawn    = _make_sound(_tone(250, 700, 0.25, noise=0.7) * 0.5, 0.25)
            self.damage   = _make_sound(_tone(220, 60, 0.45, noise=0.2, square=True), 0.5)
            self.gameover = _make_sound(np.concatenate([
                _tone(400, 300, 0.3, square=True),
                _tone(300, 200, 0.3, square=True),
                _tone(200, 90, 0.7, square=True)]), 0.45)
            self._load_files()
            self.enabled = True
        except pygame.error:
            pass

    def _load_files(self) -> None:
        """Override synthesized sounds with files from assets/sfx (and music)."""
        def load(name: str, vol: float):
            for ext in ("ogg", "wav", "mp3"):
                p = os.path.join(_ASSETS, "sfx", f"{name}.{ext}")
                if os.path.exists(p):
                    snd = pygame.mixer.Sound(p)
                    snd.set_volume(vol)
                    return snd
            return None

        for name, vol in (("star", 0.5), ("spawn", 0.35),
                          ("damage", 0.7), ("gameover", 0.7)):
            snd = load(name, vol)
            if snd:
                setattr(self, name, snd)
        hits = []
        for p in sorted(glob.glob(os.path.join(_ASSETS, "sfx", "hit*.*"))
                        + glob.glob(os.path.join(_ASSETS, "sfx", "impactPunch_medium_*.*"))):
            snd = pygame.mixer.Sound(p)
            snd.set_volume(0.8)
            hits.append(snd)
        if hits:
            self.hit = hits

    def start_music(self) -> None:
        for p in sorted(glob.glob(os.path.join(_ASSETS, "music", "*.*"))):
            try:
                pygame.mixer.music.load(p)
                pygame.mixer.music.set_volume(0.35)
                pygame.mixer.music.play(-1)
                return
            except pygame.error:
                continue

    def music_volume(self, v: float) -> None:
        if self.enabled:
            pygame.mixer.music.set_volume(v)

    def play_hit(self, combo: int, star: bool) -> None:
        if not self.enabled:
            return
        self.hit[min(combo - 1, len(self.hit) - 1)].play()
        if star:
            self.star.play()

    def play(self, name: str) -> None:
        if self.enabled:
            getattr(self, name).play()



# ---------------------------------------------------------------------------
# Ink drawing helpers (all sprites are rendered once and cached)
# ---------------------------------------------------------------------------

_SS = 4   # supersampling factor for sprites
_blot_cache: dict = {}
_dab_cache: dict = {}


def _blot(color_idx: int, k: int) -> pygame.Surface:
    key = (color_idx, k)
    if key not in _blot_cache:
        _blot_cache[key] = theme.ink_blot(40, 100 * color_idx + k, 12,
                                          _SPLASH_COLORS[color_idx])
    return _blot_cache[key]


def _dab(r: int, alpha: int) -> pygame.Surface:
    key = (r, alpha)
    if key not in _dab_cache:
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*theme.INK, alpha), (r, r), r)
        _dab_cache[key] = s
    return _dab_cache[key]


def _ninja_sprite(size: int) -> pygame.Surface:
    """Black-hooded ninja with a vermilion headband, facing right (tails trail left)."""
    S = size * _SS
    surf = pygame.Surface((S, S), pygame.SRCALPHA)
    c = S // 2
    hr = int(S * 0.33)
    pygame.draw.circle(surf, theme.INK, (c, c), hr)
    # eye slit
    slit = pygame.Rect(0, 0, int(hr * 1.45), int(hr * 0.5))
    slit.center = (c + int(hr * 0.1), c + int(hr * 0.05))
    pygame.draw.rect(surf, theme.PAPER, slit, border_radius=slit.h // 2)
    for ex in (-0.3, 0.38):
        pygame.draw.circle(surf, theme.INK, (slit.centerx + int(ex * hr), slit.centery + 2),
                           int(hr * 0.1))
    # angry brows
    for sx, sy, ex, ey in ((-0.62, -0.02, -0.12, 0.12), (0.18, 0.12, 0.72, -0.02)):
        pygame.draw.line(surf, theme.INK,
                         (slit.centerx + sx * hr, slit.top - hr * 0.08 + sy * hr * 0.4),
                         (slit.centerx + ex * hr, slit.top - hr * 0.08 + ey * hr * 0.4),
                         max(3, int(hr * 0.1)))
    # headband + trailing tails
    by = c - int(hr * 0.5)
    bw = int(hr * 0.26)
    pygame.draw.line(surf, theme.VERMILION, (c - int(hr * 0.9), by), (c + int(hr * 0.9), by), bw)
    pygame.draw.polygon(surf, theme.VERMILION, [
        (c - hr * 0.85, by - bw / 2), (c - S * 0.49, by - hr * 0.35),
        (c - hr * 1.15, by + bw * 0.1)])
    pygame.draw.polygon(surf, theme.VERMILION_DARK, [
        (c - hr * 0.85, by + bw / 2), (c - S * 0.49, by + hr * 0.25),
        (c - hr * 1.2, by + bw * 0.3)])
    return pygame.transform.smoothscale(surf, (size, size))


def _oni_sprite(size: int) -> pygame.Surface:
    """Vermilion oni mask with horns and fangs, facing the viewer."""
    S = size * _SS
    surf = pygame.Surface((S, S), pygame.SRCALPHA)
    c = S // 2
    hr = int(S * 0.33)
    # horns
    for d in (-1, 1):
        pygame.draw.polygon(surf, theme.PAPER, [
            (c + d * hr * 0.35, c - hr * 0.75), (c + d * hr * 0.95, c - hr * 1.45),
            (c + d * hr * 0.9, c - hr * 0.45)])
        pygame.draw.polygon(surf, theme.INK, [
            (c + d * hr * 0.35, c - hr * 0.75), (c + d * hr * 0.95, c - hr * 1.45),
            (c + d * hr * 0.9, c - hr * 0.45)], max(2, S // 70))
    pygame.draw.circle(surf, theme.VERMILION, (c, c), hr)
    pygame.draw.circle(surf, theme.INK, (c, c), hr, max(3, S // 45))
    # eyes + brows
    for d in (-1, 1):
        ex, ey = c + d * hr * 0.42, c - hr * 0.12
        pygame.draw.circle(surf, theme.PAPER, (ex, ey), hr * 0.2)
        pygame.draw.circle(surf, theme.INK, (ex + d * -hr * 0.02, ey + hr * 0.03), hr * 0.09)
        pygame.draw.line(surf, theme.INK, (ex + d * hr * 0.3, ey - hr * 0.42),
                         (ex - d * hr * 0.3, ey - hr * 0.2), max(4, int(hr * 0.12)))
    # mouth with fangs
    my = c + hr * 0.45
    pygame.draw.ellipse(surf, theme.INK, (c - hr * 0.5, my - hr * 0.18, hr, hr * 0.42))
    for d in (-1, 1):
        fx = c + d * hr * 0.28
        pygame.draw.polygon(surf, theme.PAPER, [
            (fx - hr * 0.1, my - hr * 0.12), (fx + hr * 0.1, my - hr * 0.12),
            (fx, my + hr * 0.18)])
    return pygame.transform.smoothscale(surf, (size, size))


_sprite_cache: dict = {}


def _enemy_sprite(variant: str, size: int) -> pygame.Surface:
    key = (variant, size)
    if key not in _sprite_cache:
        _sprite_cache[key] = (_oni_sprite if variant == "oni" else _ninja_sprite)(size)
    return _sprite_cache[key]


# ---------------------------------------------------------------------------
# HitEffect
# ---------------------------------------------------------------------------

class HitEffect:
    _DURATION = 0.6

    def __init__(self, x: float, y: float, combo: int) -> None:
        self.x      = x
        self.y      = y
        self.combo  = combo
        self.timer  = self._DURATION
        self._cidx  = min(combo - 1, 3)
        self._blot  = _blot(self._cidx, random.randrange(4))
        self._flip  = random.random() < 0.5
        self._drops = [(random.uniform(0, math.tau), random.uniform(90, 230),
                        random.uniform(3, 8)) for _ in range(9)]
        self._label = None
        if combo > 1:
            self._label = theme.text_with_outline(
                theme.latin(40 + 6 * min(combo, 5)), f"×{combo}",
                theme.VERMILION, theme.PAPER, 3)

    @property
    def alive(self) -> bool:
        return self.timer > 0

    def update(self, dt: float) -> None:
        self.timer -= dt

    def draw(self, screen: pygame.Surface) -> None:
        p = 1.0 - self.timer / self._DURATION            # 0 -> 1
        grow = 1 - (1 - min(1.0, p * 3.5)) ** 3          # fast ink burst, then settles
        size = int((70 + 55 * min(self.combo, 4) / 4) * (0.35 + 0.65 * grow))
        alpha = int(255 * min(1.0, (1 - p) * 2.0))
        if size > 4:
            blot = pygame.transform.smoothscale(self._blot, (size, size))
            if self._flip:
                blot = pygame.transform.flip(blot, True, False)
            blot.set_alpha(alpha)
            screen.blit(blot, blot.get_rect(center=(int(self.x), int(self.y))))

        # Flying droplets
        color = _SPLASH_COLORS[self._cidx]
        for ang, speed, r in self._drops:
            d = speed * (1 - (1 - min(1.0, p * 2.2)) ** 2) * 0.6 + 20
            rr = int(r * (1 - p))
            if rr >= 1:
                pygame.draw.circle(screen, color,
                                   (int(self.x + math.cos(ang) * d),
                                    int(self.y + math.sin(ang) * d)), rr)

        if self._label is not None:
            self._label.set_alpha(alpha)
            screen.blit(self._label, self._label.get_rect(
                center=(int(self.x), int(self.y - size * 0.55 - 14 - 10 * p))))


# ---------------------------------------------------------------------------
# Enemy
# ---------------------------------------------------------------------------

class Enemy:
    def __init__(self, difficulty: float, etype: str = "ninja") -> None:
        self.etype      = etype
        self.alive      = True
        self.angle      = random.uniform(0, 360)

        if etype == "star":
            self.radius     = 20
            self._hit_px    = 70
            speed           = _BASE_SPEED * 1.65 * difficulty
        else:
            self.radius     = 38
            self._hit_px    = 160
            speed           = _BASE_SPEED * difficulty

        # Enemies only come from the left or right side
        mg = self.radius + 10
        if random.random() < 0.5:
            self.x = float(-mg)
        else:
            self.x = float(DISPLAY_W + mg)
        self.y = random.uniform(0.25, 0.75) * DISPLAY_H

        # Aim near the center (small vertical spread keeps the path mostly horizontal)
        tx = DISPLAY_W / 2 + random.uniform(-40, 40)
        ty = DISPLAY_H / 2 + random.uniform(-50, 50)
        d  = math.hypot(tx - self.x, ty - self.y)
        self.vx = (tx - self.x) / d * speed
        self.vy = (ty - self.y) / d * speed

        self.sprite = None
        if etype != "star":
            variant = "oni" if random.random() < 0.25 else "ninja"
            self.sprite = _enemy_sprite(variant, int(self.radius * 2.8))
            if variant == "ninja" and self.vx < 0:   # tails trail behind
                self.sprite = pygame.transform.flip(self.sprite, True, False)

    def update(self, dt: float, mask: np.ndarray) -> str | None:
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        spin       = 520.0 if self.etype == "star" else 0.0
        self.angle = (self.angle + spin * dt) % 360

        cx, cy = DISPLAY_W / 2, DISPLAY_H / 2
        if math.hypot(self.x - cx, self.y - cy) < 55:
            self.alive = False
            return "reached_center"

        if (self.x < -250 or self.x > DISPLAY_W + 250
                or self.y < -250 or self.y > DISPLAY_H + 250):
            self.alive = False
            return None

        if self._check_hit(mask):
            self.alive = False
            return "hit"

        return None

    def _check_hit(self, mask: np.ndarray) -> bool:
        mx = int(self.x * _SX)
        my = int(self.y * _SY)
        r  = max(1, int(self.radius * _SX))
        x1, x2 = max(0, mx - r), min(CAPTURE_W, mx + r)
        y1, y2 = max(0, my - r), min(CAPTURE_H, my + r)
        if x2 <= x1 or y2 <= y1:
            return False
        return int(np.sum(mask[y1:y2, x1:x2] > 0)) > self._hit_px

    def draw(self, screen: pygame.Surface) -> None:
        ix, iy = int(self.x), int(self.y)

        # Ink wisps trailing behind
        for i, (off, a) in enumerate(((0.045, 80), (0.09, 50), (0.135, 26)), 1):
            r = max(3, int(self.radius * (0.72 - 0.16 * i)))
            tx = ix - self.vx * off
            ty = iy - self.vy * off
            dab = _dab(r, a)
            screen.blit(dab, dab.get_rect(center=(int(tx), int(ty))))

        if self.etype == "star":
            r = int(self.radius * 1.35)
            verts = _star_polygon(self.x, self.y, r, self.angle, 4)
            pygame.draw.polygon(screen, (84, 84, 94), verts)
            pygame.draw.polygon(screen, theme.INK, verts, 3)
            pygame.draw.circle(screen, theme.PAPER, (ix, iy), int(r * 0.26))
            pygame.draw.circle(screen, theme.INK, (ix, iy), int(r * 0.26), 2)
        else:
            screen.blit(self.sprite, self.sprite.get_rect(center=(ix, iy)))


# ---------------------------------------------------------------------------
# UI surfaces (built once)
# ---------------------------------------------------------------------------

class _Ui:
    def __init__(self) -> None:
        self.f_score = theme.latin(58)
        self.f_hud   = theme.latin(32)

        self.plate = pygame.Surface((280, 84), pygame.SRCALPHA)
        pygame.draw.rect(self.plate, (*theme.PAPER, 225), self.plate.get_rect(), border_radius=14)
        pygame.draw.rect(self.plate, theme.INK, self.plate.get_rect(), 3, border_radius=14)
        pygame.draw.rect(self.plate, theme.INK_SOFT, self.plate.get_rect().inflate(-12, -12),
                         1, border_radius=9)
        self.score_seal = theme.seal("点", 46, -5)

        self.life_on  = theme.seal("命", 44, 3)
        self.life_off = theme.seal("命", 44, 3, (150, 142, 134))
        self.life_off.set_alpha(120)

        self.flash = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
        for i in range(24):
            a = int(210 * (1 - i / 24) ** 2)
            pygame.draw.rect(self.flash, (*theme.VERMILION, a),
                             (i * 7, i * 4, DISPLAY_W - i * 14, DISPLAY_H - i * 8), 8)

        self.scrim_dark  = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
        self.scrim_dark.fill((*theme.INK, 185))

        T = theme.text_with_outline
        self.over_title = T(theme.latin(120), "GAME OVER", theme.PAPER, theme.VERMILION_DARK, 4)
        self.over_hint  = T(theme.latin(40), "LEERTASTE – Neustart", theme.PAPER, theme.INK, 2)
        self.over_seal  = theme.seal("敗", 130, -7)

        self._combo: dict = {}
        self._level: dict = {}

    def combo(self, n: int) -> pygame.Surface:
        if n not in self._combo:
            self._combo[n] = theme.text_with_outline(
                theme.latin(44), f"COMBO ×{n}", theme.VERMILION, theme.PAPER, 3)
        return self._combo[n]

    def level(self, n: int) -> pygame.Surface:
        if n not in self._level:
            self._level[n] = theme.text_with_outline(
                self.f_hud, f"Level {n}", theme.INK, theme.PAPER, 2)
        return self._level[n]


def _pulse(surf: pygame.Surface) -> pygame.Surface:
    surf.set_alpha(int(185 + 70 * math.sin(pygame.time.get_ticks() / 260)))
    return surf


# ---------------------------------------------------------------------------
# KungFuGame
# ---------------------------------------------------------------------------

class KungFuGame:
    _LIVES = 3

    def __init__(self) -> None:
        self.sounds = Sounds()
        self.sounds.start_music()
        self._ui = _Ui()
        self.reset()

    def reset(self) -> None:
        self.sounds.music_volume(0.35)
        self.enemies:      list[Enemy]      = []
        self.effects:      list[HitEffect]  = []
        self.score:        int              = 0
        self.lives:        int              = self._LIVES
        self.combo:        int              = 0
        self._combo_timer: float            = 0.0
        self._spawn_timer: float            = 0.0
        self._elapsed:     float            = 0.0
        self._flash:       float            = 0.0
        self.state:        str              = "playing"

    @property
    def _difficulty(self) -> float:
        return 1.0 + self._elapsed * 0.035

    @property
    def _spawn_interval(self) -> float:
        return max(_MIN_SPAWN, _SPAWN_RATE / self._difficulty)

    def update(self, dt: float, mask: np.ndarray) -> None:
        if self.state != "playing":
            return

        self._elapsed      += dt
        self._combo_timer   = max(0.0, self._combo_timer - dt)
        self._flash         = max(0.0, self._flash - dt)

        if self._combo_timer <= 0:
            self.combo = 0

        # Spawn
        self._spawn_timer += dt
        if self._spawn_timer >= self._spawn_interval:
            self._spawn_timer = 0.0
            star_chance = 0.2 * min(self._difficulty, 2.5)
            etype = "star" if random.random() < star_chance else "ninja"
            self.enemies.append(Enemy(self._difficulty, etype))
            self.sounds.play("spawn")

        # Update
        for enemy in self.enemies:
            result = enemy.update(dt, mask)
            if result == "hit":
                self.combo        += 1
                self._combo_timer  = _COMBO_TIMEOUT
                self.score        += 10 * self.combo
                self.effects.append(HitEffect(enemy.x, enemy.y, self.combo))
                self.sounds.play_hit(self.combo, enemy.etype == "star")
            elif result == "reached_center":
                self.lives -= 1
                self._flash = 0.45
                self.combo  = 0
                if self.lives <= 0:
                    self.state = "game_over"
                    self.sounds.play("gameover")
                    self.sounds.music_volume(0.1)
                else:
                    self.sounds.play("damage")

        self.enemies = [e for e in self.enemies if e.alive]

        for effect in self.effects:
            effect.update(dt)
        self.effects = [e for e in self.effects if e.alive]

    def draw(self, screen: pygame.Surface) -> None:
        ui = self._ui

        for enemy in self.enemies:
            enemy.draw(screen)
        for effect in self.effects:
            effect.draw(screen)

        # Damage flash: vermilion bleeding in from the edges
        if self._flash > 0:
            ui.flash.set_alpha(int(255 * self._flash / 0.45))
            screen.blit(ui.flash, (0, 0))

        # Score plate (top center)
        px = DISPLAY_W // 2 - ui.plate.get_width() // 2
        screen.blit(ui.plate, (px, 14))
        screen.blit(ui.score_seal, (px - 54, 28))
        sc = ui.f_score.render(str(self.score), True, theme.INK)
        screen.blit(sc, sc.get_rect(center=(DISPLAY_W // 2, 14 + 44)))

        # Lives (top right, red seals)
        for i in range(self._LIVES):
            seal = ui.life_on if i < self.lives else ui.life_off
            screen.blit(seal, (DISPLAY_W - 66 - i * 58, 22))

        # Combo banner
        if self.combo > 1 and self._combo_timer > 0:
            cb = ui.combo(self.combo)
            screen.blit(cb, cb.get_rect(center=(DISPLAY_W // 2, 128)))

        # Difficulty (bottom left)
        lvl = ui.level(int(self._difficulty))
        screen.blit(lvl, (36, DISPLAY_H - 64))

        # Game over overlay
        if self.state == "game_over":
            screen.blit(ui.scrim_dark, (0, 0))
            cx, cy = DISPLAY_W // 2, DISPLAY_H // 2
            screen.blit(ui.over_seal, ui.over_seal.get_rect(center=(cx, cy - 170)))
            screen.blit(ui.over_title, ui.over_title.get_rect(center=(cx, cy - 20)))
            sc2 = ui.f_score.render(f"Punkte: {self.score}", True, theme.PAPER)
            screen.blit(sc2, sc2.get_rect(center=(cx, cy + 75)))
            screen.blit(_pulse(ui.over_hint), ui.over_hint.get_rect(center=(cx, cy + 160)))
