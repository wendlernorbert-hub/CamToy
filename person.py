import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "models", "selfie_segmenter.tflite")
_THRESH = 0.35      # lower than 0.5 -> hands/arms drop out less
_DECAY  = 0.75      # fast-moving hands stay in the mask for a few frames
_NEAR_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))   # = 68 px at full res
_CLOSE_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))


class PersonSegmenter:
    """Selfie segmentation (same idea as Teams/Meet background blur)."""

    def __init__(self) -> None:
        opts = vision.ImageSegmenterOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_MODEL),
            running_mode=vision.RunningMode.VIDEO,
            output_confidence_masks=True,
            output_category_mask=False,
        )
        self._seg = vision.ImageSegmenter.create_from_options(opts)
        self._ts = 0
        self._prev: np.ndarray | None = None

    def update(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Return float32 person confidence (0..1) at frame resolution,
        NOT flipped (same orientation as the camera frame)."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._ts += 33
        res = self._seg.segment_for_video(img, self._ts)
        conf = res.confidence_masks[0].numpy_view()
        return np.array(conf, dtype=np.float32).reshape(frame_bgr.shape[:2])

    def refine(self, conf: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """conf (float 0..1, already flipped). Returns two uint8 0/255 masks:
        (display, hit_zone). display is the sharp person silhouette (kept briefly
        over time so fast hands don't flicker out); hit_zone is a generous area
        around it where motion counts as a hit."""
        if self._prev is not None:
            conf = np.maximum(conf, self._prev * _DECAY)
        self._prev = conf

        body = (conf > _THRESH).view(np.uint8) * 255
        body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, _CLOSE_K)

        # The generous hit zone doesn't need full resolution: dilate at 1/4 size
        h, w = body.shape
        small = cv2.resize(body, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
        small = cv2.dilate(small, _NEAR_K)
        return body, cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    def close(self) -> None:
        self._seg.close()
