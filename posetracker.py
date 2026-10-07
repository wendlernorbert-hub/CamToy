"""MediaPipe pose tracking for the mini-games, fed by the shared camera grabber.

Runs in its own thread, but only while `active` - in the classic Ninja mode the
selfie segmenter is used instead and this thread idles (saves CPU).
Output format (same as the original tracker): mirrored RGB frame, landmarks with the
x axis mirrored (so "left" is the player's left on screen), optional person mask.
"""
import os
import threading
import time

import numpy as np

_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "models", "pose_landmarker_lite.task")


def _parse(res, seg):
    if not res.pose_landmarks:
        return None, None
    arr = np.array([[p.x, p.y, p.visibility if p.visibility is not None else 0.0]
                    for p in res.pose_landmarks[0]], dtype=np.float32)
    mask = None
    if seg and getattr(res, "segmentation_masks", None):
        mask = np.squeeze(np.array(res.segmentation_masks[0].numpy_view(), dtype=np.float32))
    return arr, mask


class _Landmarker:
    def __init__(self, seg: bool) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        self.mp, self.seg = mp, seg
        self.lm = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_MODEL),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
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
    def __init__(self, grabber, size=(640, 480)) -> None:
        self._grabber = grabber
        self.size = size
        self.lock = threading.Lock()
        self.frame = self.lm = self.mask = None
        self.frame_id = 0
        self.fps = 0.0
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
        with self.lock:
            return self.frame_id, self.frame, self.lm, self.mask

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    # ---- worker ----
    def _run(self) -> None:
        import cv2
        landmarker, cur_seg = None, None
        last_seq = 0
        last_valid, last_lm, last_mask = 0.0, None, None
        t0, n = time.time(), 0
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
                rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                lm, mask = landmarker.process(rgb)
                now = time.time()
                if lm is not None:
                    lm[:, 0] = 1.0 - lm[:, 0]                 # mirror
                    if mask is not None:
                        mask = mask[:, ::-1]
                    last_valid, last_lm, last_mask = now, lm, mask
                elif now - last_valid < 0.3:                  # bridge short dropouts
                    lm, mask = last_lm, last_mask
                disp = np.ascontiguousarray(rgb[:, ::-1])
                with self.lock:
                    self.frame, self.lm, self.mask = disp, lm, mask
                    self.frame_id += 1
                n += 1
                if now - t0 >= 1.0:
                    self.fps, t0, n = n / (now - t0), now, 0
        except Exception as e:  # noqa: BLE001
            self.error = str(e)
            self.ready.set()
        finally:
            if landmarker:
                landmarker.close()
