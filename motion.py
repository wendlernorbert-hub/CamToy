import cv2
import numpy as np

CAPTURE_W = 640
CAPTURE_H = 480

_SCALE    = 0.5
_THRESH   = 25
_BLUR     = 5
_DILATE   = 8
_ALPHA    = 0.12


class MotionDetector:
    def __init__(self) -> None:
        self._bg: np.ndarray | None = None
        self._kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (_DILATE * 2 + 1, _DILATE * 2 + 1),
        )

    def update(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Return binary mask (0/255) at CAPTURE resolution, horizontally flipped
        to match the mirrored display."""
        sw = int(CAPTURE_W * _SCALE)
        sh = int(CAPTURE_H * _SCALE)
        small = cv2.resize(frame_bgr, (sw, sh), interpolation=cv2.INTER_LINEAR)
        gray  = cv2.GaussianBlur(
            cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (_BLUR, _BLUR), 0
        )

        if self._bg is None:
            self._bg = gray.astype(np.float32)
            return np.zeros((CAPTURE_H, CAPTURE_W), dtype=np.uint8)

        cv2.accumulateWeighted(gray, self._bg, _ALPHA)
        diff = cv2.absdiff(gray, cv2.convertScaleAbs(self._bg))
        _, mask_small = cv2.threshold(diff, _THRESH, 255, cv2.THRESH_BINARY)
        mask_small = cv2.morphologyEx(mask_small, cv2.MORPH_DILATE, self._kernel)

        mask = cv2.resize(mask_small, (CAPTURE_W, CAPTURE_H),
                          interpolation=cv2.INTER_NEAREST)
        return cv2.flip(mask, 1)
