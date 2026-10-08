"""MediaPipe pose tracking for the mini-games, fed by the shared camera grabber.

Runs in its own thread. One child plays, but others may be in the picture (a parent, a
sibling walking by): up to three people are tracked, so the child is not dropped in favour
of them - pose.PlayerPicker then picks the child. Every person keeps a "slot" from frame to
frame, and their landmarks are smoothed (one-euro filter: calm when still, no lag when the
hand swings).
Output: mirrored RGB frame (cropped to the screen's shape), a list of (slot, landmarks)
with the x axis mirrored (so "left" is the player's left on screen), optional person mask.
"""
import math
import os
import threading
import time

import numpy as np

_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "models", "pose_landmarker_lite.task")
MAX_PEOPLE = 3
MATCH_DIST = 0.3        # a person may move this far (screen fractions) between two frames
BRIDGE = 0.3            # seconds a lost person is still reported (short dropouts)


def _parse(res, seg):
    """-> (landmarks per person, mask per person in the same order, or None)."""
    people = [np.array([[p.x, p.y, p.visibility if p.visibility is not None else 0.0] for p in lms],
                       dtype=np.float32) for lms in (res.pose_landmarks or [])]
    masks = None
    if seg and getattr(res, "segmentation_masks", None):
        masks = [np.squeeze(np.array(m.numpy_view(), dtype=np.float32)) for m in res.segmentation_masks]
    return people, masks


def _crop(img, aspect):
    """Cuts the middle part out of a picture that is taller than `aspect` (width / height),
    e.g. 4:3 camera -> 16:9 screen. The legs are never in view anyway, so nothing is lost."""
    if not aspect:
        return img
    h, w = img.shape[:2]
    want = int(round(w / aspect))
    if want >= h:
        return img
    y0 = (h - want) // 2
    return img[y0:y0 + want]


def _centre(lm):
    """Where a person is: mean of the visible upper-body points (head, shoulders, arms)."""
    pts = lm[:17]
    vis = pts[:, 2] > 0.3
    pts = pts[vis] if vis.any() else pts
    return pts[:, :2].mean(axis=0)


class OneEuro:
    """One-euro filter for all landmark coordinates at once (Casiez et al. 2012)."""

    def __init__(self, min_cut=1.4, beta=3.5, d_cut=1.0):
        self.min_cut, self.beta, self.d_cut = min_cut, beta, d_cut
        self.x = self.dx = None
        self.t = 0.0

    @staticmethod
    def _alpha(dt, cut):
        return 1.0 / (1.0 + 1.0 / (2 * math.pi * cut * dt))

    def __call__(self, x, t):
        if self.x is None:
            self.x, self.dx, self.t = x.copy(), np.zeros_like(x), t
            return self.x.copy()
        dt = max(1e-3, t - self.t)
        self.t = t
        self.dx += self._alpha(dt, self.d_cut) * ((x - self.x) / dt - self.dx)
        a = self._alpha(dt, self.min_cut + self.beta * np.abs(self.dx))
        self.x += a * (x - self.x)
        return self.x.copy()


class _Person:
    def __init__(self, slot):
        self.slot = slot
        self.filter = OneEuro()
        self.lm = None
        self.seen = 0.0

    def update(self, lm, now):
        out = lm.copy()
        out[:, :2] = self.filter(lm[:, :2].astype(np.float64), now).astype(np.float32)
        self.lm, self.seen = out, now


class People:
    """Keeps every detected person in the same slot from frame to frame."""

    def __init__(self):
        self.slots = {}
        self.slot_of = {}             # index in `found` -> slot, from the last update

    def update(self, found, now):
        free = [s for s in range(MAX_PEOPLE)]
        self.slot_of = {}
        pairs = []
        for i, lm in enumerate(found):
            c = _centre(lm)
            for s, p in self.slots.items():
                pairs.append((float(np.hypot(*(c - _centre(p.lm)))), i, s))
        used_i, used_s = set(), set()
        for d, i, s in sorted(pairs):
            if d < MATCH_DIST and i not in used_i and s not in used_s:
                self.slots[s].update(found[i], now)
                used_i.add(i)
                used_s.add(s)
                self.slot_of[i] = s
        for i, lm in enumerate(found):
            if i in used_i:
                continue
            open_ = [s for s in free if s not in self.slots]
            if not open_:                                  # take over the slot lost the longest ago
                stale = [s for s in self.slots if s not in used_s]
                if not stale:
                    continue
                open_ = [min(stale, key=lambda s: self.slots[s].seen)]
            self.slots[open_[0]] = _Person(open_[0])
            self.slots[open_[0]].update(lm, now)
            used_s.add(open_[0])
            self.slot_of[i] = open_[0]
        for s in [s for s, p in self.slots.items() if now - p.seen > BRIDGE]:
            del self.slots[s]
        return [(s, self.slots[s].lm) for s in sorted(self.slots)]


class _Landmarker:
    def __init__(self, seg: bool) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        self.mp, self.seg = mp, seg
        self.lm = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_MODEL),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=MAX_PEOPLE,
            # lower than the default 0.5: a child sitting in front of a parent is found far more
            # often (play-test shots: 11 instead of 2 of 30 with both people)
            min_pose_detection_confidence=0.3,
            min_pose_presence_confidence=0.3,
            min_tracking_confidence=0.4,
            output_segmentation_masks=seg))
        self._last_ts = 0

    def process(self, rgb):
        ts = max(int(time.monotonic() * 1000), self._last_ts + 1)
        self._last_ts = ts
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        return _parse(self.lm.detect_for_video(img, ts), self.seg)

    def close(self) -> None:
        try:
            self.lm.close()
        except Exception:  # noqa: BLE001
            pass


class PoseTracker:
    def __init__(self, grabber, size=(640, 480), aspect=None) -> None:
        self._grabber = grabber
        self.size = size
        self.aspect = aspect          # crop the camera picture to the screen's shape (no stretching)
        self.lock = threading.Lock()
        self.frame = self.mask = None
        self.people = []
        self.frame_id = 0
        self.fps = 0.0
        self.infer_ms = 0.0               # average MediaPipe time per frame (for the play-test log)
        self.error = None
        self.ready = threading.Event()
        self.active = False
        self._seg = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # ---- control (same names the games already use) ----
    def start(self) -> None:
        self._thread.start()

    def set_active(self, on: bool) -> None:
        self.active = bool(on)

    def set_segmentation(self, on: bool) -> None:
        self._seg = bool(on)

    def latest(self):
        """(frame id, mirrored RGB frame, [(slot, landmarks 33x3)], {slot: mask} or None)"""
        with self.lock:
            return self.frame_id, self.frame, self.people, self.mask

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    # ---- worker ----
    def _run(self) -> None:
        import cv2
        landmarker, cur_seg = None, None
        last_seq = 0
        people = People()
        last_mask, last_mask_t = None, 0.0
        t0, n, busy = time.time(), 0, 0.0
        try:
            landmarker, cur_seg = _Landmarker(self._seg), self._seg   # warm up the model
            self.ready.set()
            while not self._stop.is_set():
                seq, bgr = self._grabber.latest()
                if not self.active or bgr is None or seq == last_seq:
                    time.sleep(0.004 if self.active else 0.03)
                    continue
                last_seq = seq
                if cur_seg != self._seg:
                    landmarker.close()
                    landmarker, cur_seg = _Landmarker(self._seg), self._seg
                t_in = time.perf_counter()
                bgr = _crop(bgr, self.aspect)
                rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                found, masks = landmarker.process(rgb)
                busy += time.perf_counter() - t_in
                now = time.time()
                for lm in found:
                    lm[:, 0] = 1.0 - lm[:, 0]                 # mirror
                tracked = people.update(found, now)
                mask = None
                if masks:                                     # each person's own cut-out, by slot
                    mask = {people.slot_of[i]: np.ascontiguousarray(m[:, ::-1])
                            for i, m in enumerate(masks) if i in people.slot_of}
                    last_mask, last_mask_t = mask, now
                elif now - last_mask_t < BRIDGE:
                    mask = last_mask
                disp = cv2.flip(rgb, 1)
                with self.lock:
                    self.frame, self.people, self.mask = disp, tracked, mask
                    self.frame_id += 1
                n += 1
                if now - t0 >= 1.0:
                    self.infer_ms = busy / n * 1000
                    self.fps, t0, n, busy = n / (now - t0), now, 0, 0.0
        except Exception as e:  # noqa: BLE001
            self.error = str(e)
            self.ready.set()
        finally:
            if landmarker:
                landmarker.close()
