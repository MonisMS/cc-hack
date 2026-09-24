from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from app.core.db import get_engine
from app.fieldproof.metadata import haversine_m


def assign_site(project_id: UUID, lat: float | None, lng: float | None) -> UUID | None:
    if lat is None or lng is None:
        return None
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, lat, lng, radius_m
                FROM sites
                WHERE project_id = :project_id
                """
            ),
            {"project_id": str(project_id)},
        ).mappings().all()
    best: tuple[float, UUID] | None = None
    for row in rows:
        dist = haversine_m(lat, lng, float(row["lat"]), float(row["lng"]))
        radius = int(row["radius_m"] or 200)
        if dist <= radius and (best is None or dist < best[0]):
            best = (dist, UUID(str(row["id"])))
    return None if best is None else best[1]
