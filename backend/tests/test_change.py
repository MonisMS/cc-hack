import numpy as np
from PIL import Image

from app.fieldproof.change import green_cover, round5


def _img_from_array(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(arr.astype("uint8"), mode="RGB")


def test_all_green_image_is_near_100_percent():
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    arr[..., 1] = 200  # pure green, mid brightness
    result = green_cover(_img_from_array(arr))
    assert result.pct >= 99.0
    assert isinstance(result.mask_png, bytes)
    assert len(result.mask_png) > 0


def test_all_grey_image_is_zero_percent():
    arr = np.full((100, 100, 3), 128, dtype=np.uint8)
    result = green_cover(_img_from_array(arr))
    assert result.pct == 0.0


def test_green_sky_is_excluded_by_roi():
    arr = np.full((100, 100, 3), 128, dtype=np.uint8)
    top = int(100 * 0.30)
    arr[:top, :, 1] = 200  # green "sky" in the excluded top 30%
    arr[:top, :, 0] = 0
    arr[:top, :, 2] = 0
    result = green_cover(_img_from_array(arr))
    assert result.pct == 0.0


def test_round5():
    assert round5(12) == 10
    assert round5(13) == 15
    assert round5(50) == 50
    assert round5(0) == 0
