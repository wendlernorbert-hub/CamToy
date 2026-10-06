"""Ink-style loading screen: the window opens at once, heavy start-up work
(camera, models, scene rendering) runs in a worker thread while this screen
animates a progress brush stroke."""
import math
import sys
import threading
import time

import pygame

import theme
from theme import DISPLAY_W, DISPLAY_H

_BAR_W, _BAR_H = 560, 22


class _Worker(threading.Thread):
    def __init__(self, steps) -> None:
        super().__init__(daemon=True)
        self.steps = steps
        self.index = 0
        self.step_start = time.perf_counter()
        self.error: BaseException | None = None
        self.finished = False

    def run(self) -> None:
        try:
            for i, (_label, _weight, fn) in enumerate(self.steps):
                self.index = i
                self.step_start = time.perf_counter()
                fn()
        except BaseException as e:      # reported to the main thread
            self.error = e
        self.finished = True


def _static_scene() -> pygame.Surface:
    surf = pygame.Surface((DISPLAY_W, DISPLAY_H))
    surf.fill(theme.PAPER)
    pygame.draw.rect(surf, theme.INK, (10, 10, DISPLAY_W - 20, DISPLAY_H - 20), 3)
    pygame.draw.rect(surf, theme.INK_SOFT, (18, 18, DISPLAY_W - 36, DISPLAY_H - 36), 1)
    cx = DISPLAY_W // 2
    stamp = theme.seal("拳", 130, -6)
    surf.blit(stamp, stamp.get_rect(center=(cx, 230)))
    title = theme.text_with_outline(theme.latin(96), "KUNG FU", theme.INK, theme.PAPER, 3)
    surf.blit(title, title.get_rect(center=(cx, 365)))
    return surf


def _draw(screen, scene, progress: float, label_surf) -> None:
    screen.blit(scene, (0, 0))
    cx = DISPLAY_W // 2
    bx, by = cx - _BAR_W // 2, 470
    pygame.draw.rect(screen, theme.PAPER_DARK, (bx, by, _BAR_W, _BAR_H), border_radius=11)
    fill = int(_BAR_W * progress)
    if fill > 0:
        pygame.draw.rect(screen, theme.VERMILION,
                         (bx, by, max(fill, _BAR_H), _BAR_H), border_radius=11)
        # a loaded brush: wet ink drop at the stroke's tip
        pygame.draw.circle(screen, theme.VERMILION_DARK,
                           (bx + max(fill, _BAR_H) - 11, by + _BAR_H // 2), 5)
    pygame.draw.rect(screen, theme.INK, (bx, by, _BAR_W, _BAR_H), 3, border_radius=11)
    screen.blit(label_surf, label_surf.get_rect(center=(cx, by + 62)))


def run(screen: pygame.Surface, steps: list) -> BaseException | None:
    """steps: [(label, weight, callable)]. Returns the exception a step raised, if any."""
    scene = _static_scene()
    font = theme.latin(34)
    labels = [font.render(label, True, theme.INK_SOFT) for label, _, _ in steps]
    total = float(sum(w for _, w, _ in steps))
    clock = pygame.time.Clock()

    worker = _Worker(steps)
    worker.start()
    shown = 0.0

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

        if worker.error is not None:
            return worker.error

        if worker.finished:
            target = 1.0
        else:
            i = worker.index
            done = sum(w for _, w, _ in steps[:i])
            # creep toward 90 % of the running step so the bar never looks frozen
            creep = 0.9 * (1 - math.exp(-(time.perf_counter() - worker.step_start) / 1.2))
            target = (done + steps[i][1] * creep) / total

        dt = clock.tick(60) / 1000.0
        shown = max(shown, shown + (target - shown) * min(1.0, dt * 7))
        label = labels[min(worker.index, len(labels) - 1)]
        _draw(screen, scene, min(shown, 1.0), label)
        pygame.display.flip()

        if worker.finished and shown > 0.995:
            return None
