"""T04 live check: upload one real photo through Cloudinary, register it, and
watch the worker take it from `pending` to `ready`.

Requires the worker to be running (`uv run python -m app.worker`) in another
terminal, or `--run-one` runs a single job step in-process instead.

Run from backend/:
    uv run python scripts/smoke_upload.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import cloudinary.uploader  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.fieldproof import assets, cloudinary_gw, urls  # noqa: E402
from app.core.db import get_engine  # noqa: E402

SAMPLE_IMAGE = BACKEND_DIR / "samples" / "public" / "Mangrove_plantation.jpg"
PROJECT_NAME = "Smoke test"


def get_or_create_project() -> UUID:
    engine = get_engine()
    assert engine is not None, "DATABASE_URL required"
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM projects WHERE name = :name"), {"name": PROJECT_NAME}
        ).mappings().first()
        if row is not None:
            return UUID(str(row["id"]))
        project_id = uuid4()
        conn.execute(
            text("INSERT INTO projects (id, name) VALUES (:id, :name)"),
            {"id": str(project_id), "name": PROJECT_NAME},
        )
        return project_id


def poll_asset(asset_id: UUID, timeout_s: float = 30.0) -> dict:
    engine = get_engine()
    assert engine is not None
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM assets WHERE id = :id"), {"id": str(asset_id)}
            ).mappings().first()
        if row and row["status"] in ("ready", "failed"):
            return dict(row)
        time.sleep(1)
    raise TimeoutError(f"asset {asset_id} did not finish within {timeout_s}s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-one",
        action="store_true",
        help="process one worker job in-process instead of relying on a separate worker",
    )
    args = parser.parse_args()

    project_id = get_or_create_project()
    print(f"project_id = {project_id}")

    cloudinary_gw._configure()
    result = cloudinary.uploader.upload(str(SAMPLE_IMAGE), upload_preset="fp_image")
    print(f"uploaded public_id = {result['public_id']}")

    reg = assets.register_asset(
        project_id=project_id,
        cld_public_id=result["public_id"],
        cld_asset_id=result["asset_id"],
        cld_version=result["version"],
        secure_url=result["secure_url"],
        resource_type=result.get("resource_type", "image"),
        format=result.get("format"),
        width=result.get("width"),
        height=result.get("height"),
        bytes=result.get("bytes"),
        duration_s=result.get("duration"),
        consent_confirmed=True,
        image_metadata=result.get("image_metadata") or {},
        detection=(result.get("info") or {}).get("detection"),
    )
    print(f"register_asset -> {reg}")
    asset_id = UUID(reg["asset_id"])

    if args.run_one:
        from app.worker import process_one, register_handlers

        register_handlers()
        while process_one(["analyze_asset"]):
            pass

    row = poll_asset(asset_id)
    with get_engine().connect() as conn:
        tags = conn.execute(
            text("SELECT tag, source, score, rank FROM asset_tags WHERE asset_id = :id"),
            {"id": str(asset_id)},
        ).mappings().all()

    print("\nFinal asset:")
    print(f"  status: {row['status']}")
    print(f"  thumb_url: {urls.thumb_url(row)}")
    print(f"  tags: {[dict(t) for t in tags]}")
    print(f"\nasset_id = {asset_id}")


if __name__ == "__main__":
    main()
