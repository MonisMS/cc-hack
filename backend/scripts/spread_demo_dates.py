"""T16: spread the seeded demo photos' captured_at across Jan-Sep 2026.

The Wikimedia samples have no EXIF date, so seeding stamps them all with the
upload time. That makes every photo at a site the same day, so pair
suggestions (>= 7 days apart) and date-ranged reports have nothing to work
with. This script gives each site's photos evenly spaced dates (in upload
order) and marks them captured_at_source='manual'. Staged demo data, labelled
as such in the README.

Idempotent: re-running assigns the same dates.

Run from backend/:
    uv run python scripts/spread_demo_dates.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text

from app.core.db import get_engine

PROJECT_NAME = "Green Neighbourhood Initiative"
START = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
END = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)


def main() -> None:
    engine = get_engine()
    if engine is None:
        sys.exit("DATABASE_URL not set")
    with engine.begin() as conn:
        sites = conn.execute(
            text(
                "SELECT s.id, s.name FROM sites s JOIN projects p ON p.id = s.project_id "
                "WHERE p.name = :name"
            ),
            {"name": PROJECT_NAME},
        ).all()
        for site_id, site_name in sites:
            ids = conn.execute(
                text("SELECT id FROM assets WHERE site_id = :sid ORDER BY created_at, id"),
                {"sid": site_id},
            ).scalars().all()
            if not ids:
                continue
            step = (END - START) / max(len(ids) - 1, 1)
            for i, asset_id in enumerate(ids):
                conn.execute(
                    text(
                        "UPDATE assets SET captured_at = :ts, captured_at_source = 'manual' "
                        "WHERE id = :id"
                    ),
                    {"ts": START + step * i, "id": asset_id},
                )
            print(f"{site_name}: {len(ids)} photos spread {START:%d %b} -> {END:%d %b}")


if __name__ == "__main__":
    main()
