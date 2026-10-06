import cv2
import numpy as np
import pygame

import theme

CAPTURE_W = 640
CAPTURE_H = 480

_NEED_COVER = 0.65    # share of the template that must be filled (thin limbs -> lenient)
_MAX_SPILL  = 0.30    # share of the person allowed outside the (tolerant) template
_HOLD_TIME  = 1.2     # seconds in position before the countdown starts
_COUNTDOWN  = 3.0


def _make_template() -> np.ndarray:
    """T-pose: arms stretched out to the sides (hands visible), legs apart, full body."""
    t = np.zeros((CAPTURE_H, CAPTURE_W), np.uint8)
    cv2.ellipse(t, (320, 78), (30, 38), 0, 0, 360, 255, -1)           # head
    cv2.rectangle(t, (306, 110), (334, 135), 255, -1)                 # neck
    cv2.fillPoly(t, [np.array([(262, 135), (378, 135), (368, 290),    # torso
                               (272, 290)], np.int32)], 255)
    cv2.rectangle(t, (70, 135), (570, 165), 255, -1)                  # outstretched arms
    for cx in (62, 578):
        cv2.ellipse(t, (cx, 150), (30, 24), 0, 0, 360, 255, -1)       # hands
    cv2.fillPoly(t, [np.array([(272, 285), (322, 285), (305, 470),    # left leg
                               (252, 470)], np.int32)], 255)
    cv2.fillPoly(t, [np.array([(318, 285), (368, 285), (388, 470),    # right leg
                               (335, 470)], np.int32)], 255)
    return t


def _overlay(template: np.ndarray, rgb: tuple, size: tuple) -> pygame.Surface:
    edge = cv2.morphologyEx(template, cv2.MORPH_GRADIENT,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    arr = np.zeros((CAPTURE_H, CAPTURE_W, 4), np.uint8)
    arr[..., :3] = rgb
    arr[..., 3] = np.where(edge > 0, 255, np.where(template > 0, 55, 0))
    surf = pygame.image.frombuffer(arr.tobytes(), (CAPTURE_W, CAPTURE_H), "RGBA")
    return pygame.transform.smoothscale(surf, size).convert_alpha()


class PositionGuide:
    """Start phase: wait until the player fills the silhouette, then count down."""

    def __init__(self, size: tuple) -> None:
        self._tmpl  = _make_template()
        self._tol   = cv2.dilate(self._tmpl, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
        self._area  = float(np.count_nonzero(self._tmpl))
        self._white = _overlay(self._tmpl, theme.INK_SOFT, size)   # not in position yet
        self._green = _overlay(self._tmpl, theme.MATCHA, size)     # in position
        self._texts: dict = {}
        self.reset()

    def reset(self) -> None:
        self.cover = 0.0
        self.ok    = False
        self._hold = 0.0
        self._cd   = 0.0
        self.counting = False

    @property
    def seconds_left(self) -> int:
        return max(1, int(np.ceil(_COUNTDOWN - self._cd)))

    @property
    def hold_progress(self) -> float:
        return min(1.0, self._hold / _HOLD_TIME)

    def update(self, dt: float, person: np.ndarray) -> bool:
        """person: uint8 0/255 in capture space. Returns True when the game should start."""
        inside = np.count_nonzero(cv2.bitwise_and(person, self._tmpl))
        total  = max(1, np.count_nonzero(person))
        spill  = 1.0 - np.count_nonzero(cv2.bitwise_and(person, self._tol)) / total
        self.cover = inside / self._area
        self.ok    = self.cover >= _NEED_COVER and spill <= _MAX_SPILL

        if not self.ok:
            self._hold = 0.0
            self._cd   = 0.0
            self.counting = False
            return False

        if not self.counting:
            self._hold += dt
            if self._hold >= _HOLD_TIME:
                self.counting = True
            return False

        self._cd += dt
        return self._cd >= _COUNTDOWN

    def _text(self, msg: str, size: int, color) -> pygame.Surface:
        key = (msg, size, color)
        if key not in self._texts:
            self._texts[key] = theme.text_with_outline(theme.latin(size), msg, color,
                                                       theme.PAPER, 3)
        return self._texts[key]

    def draw(self, screen: pygame.Surface, pos: tuple, font=None, font_big=None) -> None:
        # font / font_big are accepted for backwards compatibility; the theme provides fonts
        screen.blit(self._green if self.ok else self._white, pos)
        w, h = self._white.get_size()
        cx = pos[0] + w // 2

        if self.counting:
            big = self._text(str(self.seconds_left), 220, theme.MATCHA)
            screen.blit(big, big.get_rect(center=(cx, pos[1] + h // 2)))
            txt = self._text("Bleib so!", 44, theme.MATCHA)
        elif self.ok:
            txt = self._text("Perfekt – halten ...", 44, theme.MATCHA)
        else:
            txt = self._text("Arme ausbreiten – Hände und Beine in den Umriss", 40, theme.INK)
        screen.blit(txt, txt.get_rect(midtop=(cx, 30)))

        # progress bar: fill level of the silhouette, like an ink stroke on a scroll
        bw, bh = 320, 16
        bx, by = cx - bw // 2, 96
        pygame.draw.rect(screen, theme.PAPER, (bx, by, bw, bh), border_radius=8)
        fill = int(bw * min(1.0, self.cover / _NEED_COVER))
        if fill > 0:
            pygame.draw.rect(screen, theme.MATCHA if self.ok else theme.VERMILION,
                             (bx, by, max(fill, bh), bh), border_radius=8)
        pygame.draw.rect(screen, theme.INK, (bx, by, bw, bh), 3, border_radius=8)
