"""End-to-end smoke run of main.py without a window or webcam.

A fake camera repeats one picture (optional argument: a photo/screenshot with people in it),
MediaPipe runs for real. The menu picks every game in turn; each game runs a few seconds.
Aufruf:  python tests/smoke_main.py [bild.jpg]
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("CAMTOY_LOG", "0")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pygame  # noqa: E402

import main  # noqa: E402

img = cv2.imread(sys.argv[1]) if len(sys.argv) > 1 else None
if img is None:
    img = np.full((480, 640, 3), 120, np.uint8)
elif img.shape[:2] != (480, 640):          # e.g. a 16:9 screenshot: pad to 4:3 instead of stretching
    img = cv2.resize(img, (640, int(img.shape[0] * 640 / img.shape[1])))
    pad = (480 - img.shape[0]) // 2
    img = cv2.copyMakeBorder(img, pad, 480 - img.shape[0] - pad, 0, 0, cv2.BORDER_REPLICATE)


class FakeCap:
    def read(self):
        time.sleep(1 / 30)
        return True, img.copy()

    def get(self, prop):
        return {cv2.CAP_PROP_FRAME_WIDTH: 640, cv2.CAP_PROP_FRAME_HEIGHT: 480}.get(prop, 0)

    def set(self, *a):
        return True

    def release(self):
        pass


main.open_camera = lambda attempts=8: (FakeCap(), 0)
pygame.display.set_mode = (lambda f: lambda size, flags=0, vsync=0: f(size))(pygame.display.set_mode)
pygame.display.toggle_fullscreen = lambda: None

import menu  # noqa: E402
from minigames import common  # noqa: E402

state = {"game": 0, "t0": None, "seen": []}
_menu_update = menu.Menu.update


def menu_update(self, dt, pose):
    _menu_update(self, dt, pose)
    if self.t > 1.0:
        self.t = 0.0
        if state["game"] >= 6:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return None
        state["game"] += 1
        return state["game"] - 1
    return None


_game_update = common.Game.update


def game_update(self, dt, pose):
    _game_update(self, dt, pose)
    if self.t > 3.5:
        state["seen"].append((type(self).__name__, self.state, len(pose.all) if pose else 0))
        self.exit = True


menu.Menu.update = menu_update
common.Game.update = game_update
threading.Timer(120, lambda: os._exit(3)).start()       # never hang
t = time.perf_counter()
main.main()
print("games run:", state["seen"])
print("seconds:", round(time.perf_counter() - t, 1), flush=True)
os._exit(0 if len(state["seen"]) == 6 else 1)
