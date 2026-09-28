"""The only place display URLs (thumb/compare/analysis) are built. See docs/04-roadmap.md §2."""

from __future__ import annotations

from typing import Any

from app.fieldproof import cloudinary_gw
from app.fieldproof.transforms import NamedTransform


def thumb_url(row: Any) -> str:
    return cloudinary_gw.url(row["cld_public_id"], NamedTransform.THUMB, resource_type=row["resource_type"])


def compare_url(row: Any) -> str:
    return cloudinary_gw.url(row["cld_public_id"], NamedTransform.COMPARE, resource_type=row["resource_type"])


def analysis_url(row: Any) -> str:
    return cloudinary_gw.url(row["cld_public_id"], NamedTransform.ANALYSIS, resource_type=row["resource_type"])


def mask_url(public_id: str) -> str:
    return cloudinary_gw.raw_url(public_id, [{"fetch_format": "auto", "quality": "auto"}])
