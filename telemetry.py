"""Play-test recorder: performance numbers, game events and screenshots in logs/<start time>/.

* events.log  - one line per event: "  12.34  kind  key=value ...". Once a second a "perf" line
                (render fps, CPU ms per frame, tracker fps + inference ms, camera fps, pose quality).
* shots/      - a small JPEG every few seconds, plus a full-size one for every mark (key M).

On when running from source; in the exe only with CAMTOY_LOG=1. F3 shows the numbers on screen.
"""
import os
import sys
import threading
import time

import numpy as np

ROOT = (os.path.join(os.path.expanduser("~"), "Pictures", "CamToy", "logs") if getattr(sys, "frozen", False)
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
SHOT_EVERY = 4.0


def enabled() -> bool:
    flag = os.environ.get("CAMTOY_LOG", "").strip()
    if flag:
        return flag != "0"
    return not getattr(sys, "frozen", False)


class Telemetry:
    def __init__(self, on: bool = True) -> None:
        self.on = on
        self.t0 = time.perf_counter()
        self.overlay = False
        self.stats = ""                     # last perf line, for the F3 overlay
        self._work, self._loop = [], []
        self._pose_ok = self._frames = self._hands = self._people = 0
        self._last_perf = self._last_shot = self.t0
        self._shot_n = 0
        self._f = None
        if not on:
            return
        self.dir = os.path.join(ROOT, time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(os.path.join(self.dir, "shots"), exist_ok=True)
        self._f = open(os.path.join(self.dir, "events.log"), "w", encoding="utf-8", buffering=1)
        self.event("start", dir=self.dir)

    def event(self, kind: str, **kw) -> None:
        if not self._f:
            return
        t = time.perf_counter() - self.t0
        extra = " ".join(f"{k}={v}" for k, v in kw.items())
        self._f.write(f"{t:8.2f}  {kind:8s} {extra}\n")

    def frame(self, work_ms: float, loop_ms: float, pose) -> None:
        """Called once per rendered frame: CPU time for update+draw and the full loop time."""
        self._work.append(work_ms)
        self._loop.append(loop_ms)
        self._frames += 1
        if pose is not None and pose.ok:
            self._pose_ok += 1
            self._hands += len(pose.hand_points())
            self._people += len(pose.all)

    def tick(self, screen, phase: str, tracker, grabber) -> None:
        now = time.perf_counter()
        if now - self._last_perf >= 1.0 and self._work:
            span = now - self._last_perf
            work, loop = np.array(self._work), np.array(self._loop)
            self.stats = (f"fps={len(loop) / span:.0f} work={work.mean():.1f}/{work.max():.1f}ms "
                          f"loop_max={loop.max():.0f}ms track={tracker.fps:.0f}fps "
                          f"infer={tracker.infer_ms:.0f}ms cam={grabber.fps:.0f}fps "
                          f"pose={self._pose_ok / max(1, self._frames):.0%} "
                          f"hands={self._hands / max(1, self._pose_ok):.1f} "
                          f"people={self._people / max(1, self._pose_ok):.1f}")
            self.event("perf", phase=phase, **dict(kv.split("=") for kv in self.stats.split()))
            self._work.clear()
            self._loop.clear()
            self._pose_ok = self._frames = self._hands = self._people = 0
            self._last_perf = now
        if self._f and now - self._last_shot >= SHOT_EVERY:
            self._last_shot = now
            self._shot(screen, (640, 360), f"{self._shot_n:04d}_{phase}")

    def mark(self, screen, phase: str) -> None:
        """Key M: the player wants me to look at this moment."""
        self.event("MARK", phase=phase, shot=f"{self._shot_n:04d}_MARK")
        self._shot(screen, screen.get_size(), f"{self._shot_n:04d}_MARK")

    def _shot(self, screen, size, name: str) -> None:
        import pygame
        small = screen.copy() if size == screen.get_size() else pygame.transform.scale(screen, size)
        rgb = pygame.surfarray.array3d(small).swapaxes(0, 1)
        path = os.path.join(self.dir, "shots", name + ".jpg")
        self._shot_n += 1
        threading.Thread(target=_save, args=(path, rgb), daemon=True).start()

    def draw_overlay(self, screen) -> None:
        if not self.overlay or not self.stats:
            return
        from minigames.common import text
        text(screen, self.stats, 20, (12, screen.get_height() - 16), (255, 255, 160), anchor="midleft")

    def close(self) -> None:
        if self._f:
            self.event("end")
            self._f.close()
            self._f = None


def _save(path: str, rgb: np.ndarray) -> None:
    import cv2
    cv2.imwrite(path, cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, 80])
