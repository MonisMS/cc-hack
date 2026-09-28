from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image

from app.core.config import settings

EPS = 1e-6
BRIGHTNESS_MIN = 20
BRIGHTNESS_MAX = 240
ROI_TOP_FRACTION = 0.30
GREEN_TINT_OPACITY = 0.6
DARKEN_BRIGHTNESS = 0.4


@dataclass
class GreenResult:
    pct: float
    mask_png: bytes


def round5(x: float) -> float:
    return 5 * round(x / 5)


def green_cover(img: Image.Image) -> GreenResult:
    arr = np.asarray(img.convert("RGB"), dtype=np.float64)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

    s = r + g + b + EPS
    rn, gn, bn = r / s, g / s, b / s
    exg = 2 * gn - rn - bn

    brightness = (r + g + b) / 3
    height = arr.shape[0]
    roi_start = int(height * ROI_TOP_FRACTION)
    roi_mask = np.zeros(arr.shape[:2], dtype=bool)
    roi_mask[roi_start:, :] = True

    valid_mask = roi_mask & (brightness >= BRIGHTNESS_MIN) & (brightness <= BRIGHTNESS_MAX)
    green_mask = valid_mask & (exg > settings.green_exg_threshold)

    valid_count = int(valid_mask.sum())
    green_count = int(green_mask.sum())
    pct = (green_count / valid_count * 100) if valid_count > 0 else 0.0

    mask_png = _build_mask_png(arr, roi_mask, green_mask)
    return GreenResult(pct=pct, mask_png=mask_png)


def _build_mask_png(arr: np.ndarray, roi_mask: np.ndarray, green_mask: np.ndarray) -> bytes:
    out = arr.copy()

    darken_mask = roi_mask & ~green_mask
    out[darken_mask] = arr[darken_mask] * DARKEN_BRIGHTNESS

    green_color = np.array([0, 255, 0], dtype=np.float64)
    out[green_mask] = arr[green_mask] * (1 - GREEN_TINT_OPACITY) + green_color * GREEN_TINT_OPACITY

    excluded_mask = ~roi_mask
    gray = arr[excluded_mask].mean(axis=-1, keepdims=True)
    out[excluded_mask] = np.repeat(gray, 3, axis=-1)

    out_img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")
    buf = io.BytesIO()
    out_img.save(buf, format="PNG")
    return buf.getvalue()
