from __future__ import annotations

from enum import StrEnum

from app.core.config import settings


class NamedTransform(StrEnum):
    THUMB = "THUMB"
    ANALYSIS = "ANALYSIS"
    COMPARE = "COMPARE"
    SQUARE = "SQUARE"
    STORY = "STORY"
    QUOTE_CARD = "QUOTE_CARD"
    COLLAGE = "COLLAGE"
    VIDEO_FRAME = "VIDEO_FRAME"


def _gravity() -> str:
    return "auto" if settings.enable_g_auto else "center"


def _blur_faces() -> list[dict]:
    return [{"effect": "blur_faces"}] if settings.enable_blur_faces else []


def TRANSFORMS() -> dict[NamedTransform, list[dict]]:
    g = _gravity()
    return {
        NamedTransform.THUMB: [
            {"crop": "fill", "gravity": g, "width": 320, "height": 240},
            {"fetch_format": "auto", "quality": "auto"},
        ],
        NamedTransform.ANALYSIS: [
            {"crop": "limit", "width": 1024},
            {"fetch_format": "jpg"},
        ],
        NamedTransform.COMPARE: [
            {"crop": "fill", "gravity": g, "width": 800, "height": 600},
            *_blur_faces(),
            {"fetch_format": "jpg"},
        ],
        NamedTransform.SQUARE: [
            {"crop": "fill", "gravity": g, "width": 1080, "height": 1080},
            *_blur_faces(),
            {"fetch_format": "auto", "quality": "auto"},
        ],
        NamedTransform.STORY: [
            {"crop": "fill", "gravity": g, "width": 1080, "height": 1920},
            *_blur_faces(),
            {"fetch_format": "auto", "quality": "auto"},
        ],
        NamedTransform.QUOTE_CARD: [
            {"crop": "fill", "gravity": g, "width": 1080, "height": 1080},
            *_blur_faces(),
            {"fetch_format": "auto", "quality": "auto"},
        ],
        NamedTransform.COLLAGE: [
            {"crop": "fill", "width": 800, "height": 600},
            {"crop": "pad", "width": 1600, "height": 600, "gravity": "west"},
            *_blur_faces(),
        ],
        NamedTransform.VIDEO_FRAME: [
            {"crop": "limit", "width": 1024},
            {"fetch_format": "jpg"},
        ],
    }


def chain(preset: NamedTransform, **kw) -> list[dict]:
    steps = [dict(s) for s in TRANSFORMS()[preset]]
    if preset is NamedTransform.VIDEO_FRAME:
        t = kw.get("t", 0)
        steps = [{"start_offset": t}, *steps]
    if preset is NamedTransform.QUOTE_CARD and kw.get("text"):
        overlay_text = str(kw["text"])[:80]
        overlay_text = "".join(ch for ch in overlay_text if ord(ch) < 128 and ch.isprintable())
        steps.insert(
            -1,
            {
                "overlay": {
                    "font_family": "Arial",
                    "font_size": 48,
                    "text": overlay_text,
                },
                "gravity": "south",
                "color": "white",
            },
        )
    if preset is NamedTransform.COLLAGE and kw.get("after_public_id"):
        overlay_id = str(kw["after_public_id"]).replace("/", ":")
        steps.insert(
            -1 if settings.enable_blur_faces else len(steps),
            {"overlay": overlay_id, "crop": "fill", "width": 800, "height": 600},
        )
        steps.insert(
            -1 if settings.enable_blur_faces else len(steps),
            {"flags": "layer_apply", "gravity": "east"},
        )
    return steps
