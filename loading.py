"""Loading screen in the shared (menu) look: the window opens at once, heavy start-up work
(camera, models, scene rendering) runs in a worker thread while this screen animates a
progress bar. Deliberately neutral - it precedes the mode menu, not one particular game."""
import math
import sys
import threading
import time

import numpy as np
import pygame

from minigames.common import rainbow, text

DISPLAY_W, DISPLAY_H = 1280, 720
_BAR_W, _BAR_H = 560, 26


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
    """Same blue gradient family as the mode menu."""
    yy = np.linspace(0, 1, DISPLAY_H, dtype=np.float32)[:, None, None]
    xx = np.linspace(0, 1, DISPLAY_W, dtype=np.float32)[None, :, None]
    top, bot = np.float32((52, 70, 160)), np.float32((50, 130, 150))
    arr = top * (1 - yy) + bot * yy
    arr = arr * (1 - 0.15 * xx) + np.float32((90, 70, 130)) * 0.15 * xx
    surf = pygame.surfarray.make_surface(np.clip(arr, 0, 255).astype(np.uint8)
                                         .repeat(1, axis=0).swapaxes(0, 1))
    return surf.convert()


def _draw(screen, scene, progress: float, label: str, t: float) -> None:
    screen.blit(scene, (0, 0))
    cx = DISPLAY_W // 2
    title = "CamToy"
    f_w = 96
    x = cx - len(title) * f_w / 2 + f_w / 2
    for i, ch in enumerate(title):
        text(screen, ch, 150, (x + i * f_w, 270 + 8 * math.sin(t * 3 + i)), rainbow(i, 6, .6))

    bx, by = cx - _BAR_W // 2, 450
    pygame.draw.rect(screen, (255, 255, 255, 90), (bx - 4, by - 4, _BAR_W + 8, _BAR_H + 8),
                     border_radius=17)
    pygame.draw.rect(screen, (40, 50, 120), (bx, by, _BAR_W, _BAR_H), border_radius=13)
    fill = int(_BAR_W * progress)
    if fill > 0:
        pygame.draw.rect(screen, (255, 225, 60), (bx, by, max(fill, _BAR_H), _BAR_H),
                         border_radius=13)


def run(screen: pygame.Surface, steps: list) -> BaseException | None:
    """steps: [(label, weight, callable)]. Returns the exception a step raised, if any."""
    scene = _static_scene()
    total = float(sum(w for _, w, _ in steps))
    clock = pygame.time.Clock()

    worker = _Worker(steps)
    worker.start()
    shown, t = 0.0, 0.0

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
        t += dt
        shown = max(shown, shown + (target - shown) * min(1.0, dt * 7))
        label = steps[min(worker.index, len(steps) - 1)][0]
        _draw(screen, scene, min(shown, 1.0), label, t)
        pygame.display.flip()

        if worker.finished and shown > 0.995:
            return None
