import math
import random
import pygame
import numpy as np

DISPLAY_W = 1280
DISPLAY_H = 720
CAPTURE_W = 640
CAPTURE_H = 480

_SX = CAPTURE_W / DISPLAY_W
_SY = CAPTURE_H / DISPLAY_H

_BASE_SPEED    = 140.0   # px/s at difficulty 1
_SPAWN_RATE    = 1.8     # seconds between spawns at difficulty 1
_MIN_SPAWN     = 0.45
_COMBO_TIMEOUT = 1.5     # seconds until combo resets

_COMBO_COLORS = [
    (255, 255, 255),
    (255, 220,  50),
    (255, 140,  30),
    (255,  50,  50),
]


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
# HitEffect
# ---------------------------------------------------------------------------

class HitEffect:
    def __init__(self, x: float, y: float, combo: int) -> None:
        self.x      = x
        self.y      = y
        self.combo  = combo
        self.timer  = 0.55
        self._max   = 0.55
        self.r      = 28.0

    @property
    def alive(self) -> bool:
        return self.timer > 0

    def update(self, dt: float) -> None:
        self.timer -= dt
        self.r     += 90 * dt

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        t     = max(0.0, self.timer / self._max)
        alpha = int(255 * t)
        r     = int(self.r)
        color = _COMBO_COLORS[min(self.combo - 1, 3)]
        ix, iy = int(self.x), int(self.y)

        # Expanding ring
        x1 = max(0, ix - r - 4)
        y1 = max(0, iy - r - 4)
        x2 = min(DISPLAY_W, ix + r + 4)
        y2 = min(DISPLAY_H, iy + r + 4)
        if x2 > x1 and y2 > y1:
            s = pygame.Surface((x2 - x1, y2 - y1), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, alpha), (ix - x1, iy - y1), r, 3)
            screen.blit(s, (x1, y1))

        # Combo label
        if self.combo > 1:
            label = font.render(f"×{self.combo}", True, color)
            label.set_alpha(alpha)
            screen.blit(label, (ix - label.get_width() // 2, iy - r - 32))


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
            self.color      = (255, 200, 30)
            self._hit_px    = 70
            speed           = _BASE_SPEED * 1.65 * difficulty
        else:
            self.radius     = 38
            self.color      = (190, 35, 35)
            self._hit_px    = 160
            speed           = _BASE_SPEED * difficulty

        edge = random.randint(0, 3)
        mg   = self.radius + 10
        if edge == 0:
            self.x = float(-mg)
            self.y = random.uniform(0.15, 0.85) * DISPLAY_H
        elif edge == 1:
            self.x = float(DISPLAY_W + mg)
            self.y = random.uniform(0.15, 0.85) * DISPLAY_H
        elif edge == 2:
            self.x = random.uniform(0.15, 0.85) * DISPLAY_W
            self.y = float(-mg)
        else:
            self.x = random.uniform(0.15, 0.85) * DISPLAY_W
            self.y = float(DISPLAY_H + mg)

        # Aim slightly off-center to spread enemies
        tx = DISPLAY_W / 2 + random.uniform(-100, 100)
        ty = DISPLAY_H / 2 + random.uniform(-100, 100)
        d  = math.hypot(tx - self.x, ty - self.y)
        self.vx = (tx - self.x) / d * speed
        self.vy = (ty - self.y) / d * speed

    def update(self, dt: float, mask: np.ndarray) -> str | None:
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        spin       = 130.0 if self.etype == "star" else 50.0
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
        r = self.radius

        if self.etype == "star":
            verts = _star_polygon(self.x, self.y, r, self.angle, 6)
            pygame.draw.polygon(screen, self.color, verts)
            pygame.draw.polygon(screen, (255, 255, 200),
                                _star_polygon(self.x, self.y, r * 0.38, self.angle, 6))
        else:
            # Shadow
            pygame.draw.circle(screen, (0, 0, 0), (ix + 4, iy + 4), r)
            # Body
            pygame.draw.circle(screen, self.color, (ix, iy), r)
            pygame.draw.circle(screen, (230, 230, 230), (ix, iy), r, 2)
            # Headband
            pygame.draw.line(screen, (15, 15, 15),
                             (ix - r, iy - 9), (ix + r, iy - 9), 9)
            # Eyes
            for ex in (-12, 12):
                pygame.draw.circle(screen, (255, 255, 255), (ix + ex, iy + 3), 7)
                pygame.draw.circle(screen, (10, 10, 10),   (ix + ex, iy + 3), 4)


# ---------------------------------------------------------------------------
# KungFuGame
# ---------------------------------------------------------------------------

class KungFuGame:
    _LIVES = 3

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
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

        # Update
        for enemy in self.enemies:
            result = enemy.update(dt, mask)
            if result == "hit":
                self.combo        += 1
                self._combo_timer  = _COMBO_TIMEOUT
                self.score        += 10 * self.combo
                self.effects.append(HitEffect(enemy.x, enemy.y, self.combo))
            elif result == "reached_center":
                self.lives -= 1
                self._flash = 0.45
                self.combo  = 0
                if self.lives <= 0:
                    self.state = "game_over"

        self.enemies = [e for e in self.enemies if e.alive]

        for effect in self.effects:
            effect.update(dt)
        self.effects = [e for e in self.effects if e.alive]

    def draw(self, screen: pygame.Surface,
             font: pygame.font.Font, font_big: pygame.font.Font) -> None:
        for enemy in self.enemies:
            enemy.draw(screen)
        for effect in self.effects:
            effect.draw(screen, font)

        # Red flash on life loss
        if self._flash > 0:
            alpha = int(180 * self._flash / 0.45)
            s = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
            s.fill((255, 20, 20, alpha))
            screen.blit(s, (0, 0))

        # Lives (top right, red dots)
        for i in range(self.lives):
            pygame.draw.circle(screen, (220, 50, 50),
                               (DISPLAY_W - 28 - i * 38, 28), 13)
            pygame.draw.circle(screen, (255, 120, 120),
                               (DISPLAY_W - 28 - i * 38, 28), 13, 2)

        # Score (top center)
        sc = font_big.render(str(self.score), True, (255, 255, 255))
        screen.blit(sc, (DISPLAY_W // 2 - sc.get_width() // 2, 8))

        # Combo banner
        if self.combo > 1 and self._combo_timer > 0:
            cb = font.render(f"COMBO  ×{self.combo}", True, (255, 220, 50))
            screen.blit(cb, (DISPLAY_W // 2 - cb.get_width() // 2, 68))

        # Difficulty badge (bottom left, subtle)
        lvl = font.render(f"LV {int(self._difficulty)}", True, (180, 180, 180))
        screen.blit(lvl, (12, DISPLAY_H - 36))

        # Game over overlay
        if self.state == "game_over":
            ov = pygame.Surface((DISPLAY_W, DISPLAY_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 155))
            screen.blit(ov, (0, 0))

            go  = font_big.render("GAME OVER", True, (255, 60, 60))
            sc2 = font.render(f"Score: {self.score}", True, (255, 255, 255))
            re  = font.render("LEERTASTE  –  Neustart", True, (200, 200, 200))

            cx = DISPLAY_W // 2
            cy = DISPLAY_H // 2
            screen.blit(go,  (cx - go.get_width()  // 2, cy - 90))
            screen.blit(sc2, (cx - sc2.get_width() // 2, cy))
            screen.blit(re,  (cx - re.get_width()  // 2, cy + 60))
