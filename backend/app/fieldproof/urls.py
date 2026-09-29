"""The only place display URLs (thumb/compare/analysis) are built. See docs/04-roadmap.md §2."""

from __future__ import annotations

from typing import Any

from app.fieldproof import cloudinary_gw
from app.fieldproof.transforms import NamedTransform

# Video rows are shown as a still frame (1 s in), delivered as JPG so <img> tags work.
POSTER_OFFSET_S = 1


def _url(row: Any, preset: NamedTransform) -> str:
    if row["resource_type"] == "video":
        return cloudinary_gw.url(
            row["cld_public_id"], preset, resource_type="video", t=POSTER_OFFSET_S, format="jpg"
        )
    return cloudinary_gw.url(row["cld_public_id"], preset, resource_type=row["resource_type"])


def thumb_url(row: Any) -> str:
    return _url(row, NamedTransform.THUMB)


def compare_url(row: Any) -> str:
    return _url(row, NamedTransform.COMPARE)


def analysis_url(row: Any) -> str:
    return cloudinary_gw.url(row["cld_public_id"], NamedTransform.ANALYSIS, resource_type=row["resource_type"])


def mask_url(public_id: str) -> str:
    return cloudinary_gw.raw_url(public_id, [{"fetch_format": "auto", "quality": "auto"}])


def square_url(row: Any) -> str:
    return _url(row, NamedTransform.SQUARE)


def story_url(row: Any) -> str:
    return _url(row, NamedTransform.STORY)


def collage_url(before_row: Any, after_row: Any) -> str:
    return cloudinary_gw.url(
        before_row["cld_public_id"],
        NamedTransform.COLLAGE,
        resource_type=before_row["resource_type"],
        after_public_id=after_row["cld_public_id"],
    )
