"""T06: seed the demo project with the Wikimedia sample photos across 4 sites in India.

Idempotent: skips any file whose target public_id already exists in our DB, so
re-running only uploads new samples (e.g. after fetch_more_samples.py adds more).

Requires a worker to be draining the job queue (either `uv run python -m
app.worker` in another terminal, or pass --drain to have this script process
jobs in-process after registering).

Run from backend/:
    uv run python scripts/seed_demo.py --drain
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import time
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import cloudinary.uploader  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.db import get_engine  # noqa: E402
from app.fieldproof import assets, cloudinary_gw  # noqa: E402

PUBLIC_DIR = BACKEND_DIR / "samples" / "public"
LABELS_PATH = PUBLIC_DIR / "labels.json"
PROJECT_NAME = "Green Neighbourhood Initiative"
PROJECT_STARTED_ON = date(2026, 1, 1)

# 4 sites spread across India (§5 T06). All fall inside metadata.in_india's bounds.
SITES: dict[str, tuple[float, float]] = {
    "Bengaluru": (12.9716, 77.5946),
    "Chennai coast": (13.0500, 80.2824),
    "Sundarbans": (21.9497, 88.9317),
    "Rajasthan": (26.9124, 75.7873),
}
SITE_RADIUS_M = 5000

# Which site's theme each CLIP label belongs to, so seeded photos land somewhere sensible.
LABEL_SITE: dict[str, str] = {
    "sapling": "Rajasthan",
    "mangrove": "Sundarbans",
    "flood": "Chennai coast",
    "road_construction": "Bengaluru",
    "solar": "Rajasthan",
    "classroom": "Bengaluru",
    "hand_pump": "Rajasthan",
    "waste": "Bengaluru",
    "cleanup": "Chennai coast",
    "drought": "Rajasthan",
    "deforestation": "Sundarbans",
}


def slug(filename: str) -> str:
    stem = Path(filename).stem
    s = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    return f"seed_{s}"[:100]


def random_point_near(lat: float, lng: float, max_m: float = 1000.0) -> tuple[float, float]:
    bearing = random.uniform(0, 2 * math.pi)
    dist = random.uniform(0, max_m)
    dlat = (dist * math.cos(bearing)) / 111_320.0
    dlng = (dist * math.sin(bearing)) / (111_320.0 * math.cos(math.radians(lat)))
    return lat + dlat, lng + dlng


def get_or_create_project() -> UUID:
    engine = get_engine()
    assert engine is not None, "DATABASE_URL required"
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM projects WHERE name = :n"), {"n": PROJECT_NAME}
        ).mappings().first()
        if row:
            return UUID(str(row["id"]))
        project_id = uuid4()
        conn.execute(
            text("INSERT INTO projects (id, name, started_on) VALUES (:id, :name, :started_on)"),
            {"id": str(project_id), "name": PROJECT_NAME, "started_on": PROJECT_STARTED_ON},
        )
        return project_id


def get_or_create_sites(project_id: UUID) -> dict[str, UUID]:
    engine = get_engine()
    assert engine is not None
    with engine.begin() as conn:
        existing = {
            r["name"]: UUID(str(r["id"]))
            for r in conn.execute(
                text("SELECT id, name FROM sites WHERE project_id = :pid"), {"pid": str(project_id)}
            ).mappings().all()
        }
        for name, (lat, lng) in SITES.items():
            if name in existing:
                continue
            site_id = uuid4()
            conn.execute(
                text(
                    """
                    INSERT INTO sites (id, project_id, name, lat, lng, radius_m)
                    VALUES (:id, :pid, :name, :lat, :lng, :radius_m)
                    """
                ),
                {
                    "id": str(site_id),
                    "pid": str(project_id),
                    "name": name,
                    "lat": lat,
                    "lng": lng,
                    "radius_m": SITE_RADIUS_M,
                },
            )
            existing[name] = site_id
    return existing


def asset_exists(public_id: str) -> bool:
    engine = get_engine()
    assert engine is not None
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT 1 FROM assets WHERE cld_public_id = :pid"), {"pid": public_id}
            ).first()
            is not None
        )


def wait_for_completion(project_id: UUID, timeout_s: float = 600.0) -> None:
    engine = get_engine()
    assert engine is not None
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT status, count(*) FROM assets WHERE project_id = :pid GROUP BY status"),
                {"pid": str(project_id)},
            ).all()
        counts = dict(rows)
        pending = counts.get("pending", 0) + counts.get("processing", 0)
        print(f"  status: {counts}")
        if pending == 0:
            break
        time.sleep(2)
    else:
        print("! timed out waiting for jobs to finish")

    with engine.connect() as conn:
        failed = conn.execute(
            text(
                "SELECT cld_public_id, error FROM assets WHERE project_id = :pid AND status = 'failed'"
            ),
            {"pid": str(project_id)},
        ).mappings().all()
    for f in failed:
        print(f"  FAILED {f['cld_public_id']}: {f['error']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--drain", action="store_true", help="process the job queue in-process instead of relying on a separate worker"
    )
    args = parser.parse_args()

    labels: dict[str, str] = json.loads(LABELS_PATH.read_text())
    project_id = get_or_create_project()
    site_ids = get_or_create_sites(project_id)
    print(f"project_id = {project_id}")
    print(f"sites = {{{', '.join(f'{k}: {v}' for k, v in site_ids.items())}}}")

    cloudinary_gw._configure()
    registered = 0
    skipped = 0
    for filename, label in sorted(labels.items()):
        path = PUBLIC_DIR / filename
        if not path.exists():
            print(f"! missing file, skipping: {filename}")
            continue
        public_id = slug(filename)
        if asset_exists(public_id):
            skipped += 1
            continue

        site_name = LABEL_SITE.get(label)
        if site_name is None:
            print(f"! no site mapping for label '{label}', skipping {filename}")
            continue
        site_lat, site_lng = SITES[site_name]
        device_lat, device_lng = random_point_near(site_lat, site_lng)

        result = cloudinary.uploader.upload(str(path), upload_preset="fp_image", public_id=public_id)
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
            device_lat=device_lat,
            device_lng=device_lng,
            consent_confirmed=True,
            image_metadata=result.get("image_metadata") or {},
            detection=(result.get("info") or {}).get("detection"),
        )
        registered += 1
        print(f"[{registered}] {filename} ({label} -> {site_name}) -> {reg['asset_id']}")

    print(f"\nRegistered {registered} new assets, skipped {skipped} already-seeded.")

    if args.drain:
        from app.worker import process_one, register_handlers

        register_handlers()
        n = 0
        while process_one(["analyze_asset"]):
            n += 1
        print(f"drained {n} jobs in-process")

    wait_for_completion(project_id)


if __name__ == "__main__":
    main()
