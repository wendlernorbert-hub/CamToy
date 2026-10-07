"""Kamera + MediaPipe-Pose (Tasks-API) in einem eigenen Thread.

Der Thread liefert dem Spiel immer das neueste Kamerabild (gespiegelt) und die
Landmarks (x gespiegelt, damit links = Spieler-links auf dem Bildschirm).
"""
import os
import threading
import time
import urllib.request

import numpy as np

from pose import LM, make_skeleton, STAND

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "models", "pose_landmarker_lite.task")


def ensure_model(path=MODEL_PATH):
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print("Lade Pose-Modell (einmalig, ca. 6 MB) ...")
    try:
        tmp = path + ".part"
        urllib.request.urlretrieve(MODEL_URL, tmp)
        os.replace(tmp, path)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Das Pose-Modell konnte nicht geladen werden (%s).\n"
            "Bitte manuell herunterladen:\n  %s\nund speichern als:\n  %s"
            % (e, MODEL_URL, path))
    return path


def parse_result(res, seg):
    """MediaPipe-Ergebnis -> (landmarks[33,3] oder None, maske oder None)."""
    if not res.pose_landmarks:
        return None, None
    pts = res.pose_landmarks[0]
    arr = np.array([[p.x, p.y, p.visibility if p.visibility is not None else 0.0]
                    for p in pts], dtype=np.float32)
    mask = None
    if seg and getattr(res, "segmentation_masks", None):
        mask = np.squeeze(np.array(res.segmentation_masks[0].numpy_view(),
                                   dtype=np.float32))
    return arr, mask


class _Landmarker:
    def __init__(self, model_path, seg):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        self.mp = mp
        self.seg = seg
        opts = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=seg)
        self.lm = vision.PoseLandmarker.create_from_options(opts)
        self._last_ts = 0

    def process(self, rgb):
        ts = int(time.monotonic() * 1000)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        return parse_result(self.lm.detect_for_video(img, ts), self.seg)

    def close(self):
        try:
            self.lm.close()
        except Exception:  # noqa: BLE001
            pass


class Tracker:
    def __init__(self, cam=0, width=640, height=480):
        self.cam, self.req = cam, (width, height)
        self.lock = threading.Lock()
        self.frame = self.lm = self.mask = None
        self.frame_id = 0
        self.fps = 0.0
        self.error = None
        self.size = (width, height)
        self._seg = False
        self._stop = threading.Event()
        self._thread = None
        self._cap = None
        self._model = None

    def start(self):
        import cv2
        self._cv2 = cv2
        self._model = ensure_model()
        backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.cam, backend)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.req[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.req[1])
        ok, frame = cap.read()
        if not ok:
            cap.release()
            raise RuntimeError("Keine Kamera gefunden (Index %d). Mit --kamera 1 "
                               "eine andere probieren oder --maus zum Testen." % self.cam)
        self.size = (frame.shape[1], frame.shape[0])
        self._cap = cap
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_segmentation(self, on):
        self._seg = bool(on)

    def latest(self):
        with self.lock:
            return self.frame_id, self.frame, self.lm, self.mask

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()

    def _run(self):
        cv2 = self._cv2
        landmarker, cur_seg = None, None
        last_valid, last_lm, last_mask = 0.0, None, None
        t0, n = time.time(), 0
        fails = 0
        try:
            while not self._stop.is_set():
                ok, bgr = self._cap.read()
                if not ok:
                    fails += 1
                    if fails > 100:
                        raise RuntimeError("Kamerabild bleibt aus.")
                    time.sleep(0.01)
                    continue
                fails = 0
                if landmarker is None or cur_seg != self._seg:
                    if landmarker:
                        landmarker.close()
                    cur_seg = self._seg
                    landmarker = _Landmarker(self._model, cur_seg)
                rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                lm, mask = landmarker.process(rgb)
                now = time.time()
                if lm is not None:
                    lm[:, 0] = 1.0 - lm[:, 0]            # Spiegelbild
                    if mask is not None:
                        mask = mask[:, ::-1]
                    last_valid, last_lm, last_mask = now, lm, mask
                elif now - last_valid < 0.3:             # kurze Aussetzer überbrücken
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
        finally:
            if landmarker:
                landmarker.close()


class MockTracker:
    """Ohne Kamera: Maus steuert die rechte Hand, bei gedrückter Taste beide."""

    def __init__(self, aspect=4 / 3):
        self.size = (640, int(640 / aspect))
        self.aspect = aspect
        self.error = None
        self.fps = 30.0
        self.mouse = (0.5, 0.5, False)
        self._t0 = time.time()
        w, h = self.size
        yy, xx = np.mgrid[0:h, 0:w]
        self._frame = np.dstack([(60 + 60 * xx / w), (90 + 80 * yy / h),
                                 (140 + 60 * (1 - xx / w))]).astype(np.uint8)

    def start(self):
        pass

    def stop(self):
        pass

    def set_segmentation(self, on):
        pass

    def latest(self):
        fid = int((time.time() - self._t0) * 30)
        mx, my, down = self.mouse
        lm = make_skeleton(STAND, aspect=self.aspect)
        for name in (("r_wr", "r_idx") + (("l_wr", "l_idx") if down else ())):
            lm[LM[name], 0] = mx
            lm[LM[name], 1] = my
        return fid, self._frame, lm, None
