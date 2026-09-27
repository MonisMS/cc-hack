"""T05: sanity-check that our 5 named Cloudinary transforms actually render.

Run from backend/:
    uv run python scripts/check_transforms.py <public_id> [<after_public_id>]

If <after_public_id> is omitted, <public_id> is used for both sides of COLLAGE.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402

from app.fieldproof import cloudinary_gw  # noqa: E402
from app.fieldproof.transforms import NamedTransform  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: check_transforms.py <public_id> [<after_public_id>]")
    public_id = sys.argv[1]
    after_public_id = sys.argv[2] if len(sys.argv) > 2 else public_id

    checks = [
        ("THUMB", cloudinary_gw.url(public_id, NamedTransform.THUMB)),
        ("COMPARE", cloudinary_gw.url(public_id, NamedTransform.COMPARE)),
        ("SQUARE", cloudinary_gw.url(public_id, NamedTransform.SQUARE)),
        ("STORY", cloudinary_gw.url(public_id, NamedTransform.STORY)),
        (
            "COLLAGE",
            cloudinary_gw.url(public_id, NamedTransform.COLLAGE, after_public_id=after_public_id),
        ),
    ]

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for name, url in checks:
            res = client.get(url)
            error = res.headers.get("x-cld-error", "")
            print(f"{name:8} {res.status_code}  {url}  {error}")


if __name__ == "__main__":
    main()
