"""Webcam -> sumi-e look: few grey ink washes, brushed outlines, warm paper tone."""
import cv2
import numpy as np

from theme import INK, PAPER

_WASHES = 5                      # number of ink tones
_EDGE_BLOCK = 9
_EDGE_C = 9
_OUTLINE_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))


def _build_lut() -> np.ndarray:
    """gray (0..255) -> RGB: S-curve, quantised into wash steps, ink -> paper gradient."""
    g = np.arange(256, dtype=np.float32) / 255.0
    g = np.clip((g - 0.5) * 1.35 + 0.52, 0, 1)                 # contrast
    steps = np.floor(g * _WASHES) / (_WASHES - 1)
    g = np.clip(0.5 * g + 0.5 * steps, 0, 1)                   # soft posterize
    ink, paper = np.float32(INK), np.float32(PAPER)
    rgb = ink[None, :] + (paper - ink)[None, :] * g[:, None] ** 0.9
    return np.clip(rgb, 0, 255).astype(np.uint8).reshape(256, 1, 3)


_LUT = _build_lut()


def inkify(frame_rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 -> RGB uint8 ink painting (same size)."""
    h, w = frame_rgb.shape[:2]
    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

    # Wash tones from a smoothed half-res copy (flat areas, like diluted ink)
    small = cv2.resize(gray, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    small = cv2.bilateralFilter(small, 5, 40, 5)
    wash = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    out = cv2.LUT(cv2.merge([wash, wash, wash]), _LUT)

    # Brush outlines from the sharp full-res image
    edges = cv2.adaptiveThreshold(cv2.medianBlur(gray, 5), 255,
                                  cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,
                                  _EDGE_BLOCK, _EDGE_C)
    lines = cv2.convertScaleAbs(edges, alpha=0.62, beta=0.38 * 255)
    return cv2.multiply(out, cv2.merge([lines, lines, lines]), scale=1 / 255)


def silhouette_ink(rgb: np.ndarray, person: np.ndarray) -> np.ndarray:
    """Return alpha (0/255, slightly larger than `person`) and paint a bold
    brush outline around the person into `rgb` (in place)."""
    grown = cv2.dilate(person, _OUTLINE_K)
    rgb[grown > person] = INK
    return cv2.GaussianBlur(grown, (5, 5), 0)   # soft edge: no stair-steps after upscaling
