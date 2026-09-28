from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text

from app.core.db import get_engine
from app.core.errors import ApiError

MIN_DAYS_APART = 7
TOP_N = 3


@dataclass
class PairCandidate:
    before_id: UUID
    after_id: UUID
    image_similarity: float
    days_apart: int


def pair_suggestions(site_id: UUID) -> list[PairCandidate]:
    engine = get_engine()
    if engine is None:
        raise ApiError("INTERNAL", "database not configured", 500)

    sql = """
        SELECT b.id AS before_id, a.id AS after_id,
               1 - (be.embedding <=> ae.embedding) AS image_similarity,
               EXTRACT(EPOCH FROM (a.captured_at - b.captured_at)) / 86400 AS days_apart
        FROM assets b
        JOIN assets a ON a.site_id = b.site_id AND a.captured_at > b.captured_at
        JOIN asset_embeddings be ON be.asset_id = b.id AND be.frame_s = 0
        JOIN asset_embeddings ae ON ae.asset_id = a.id AND ae.frame_s = 0
        WHERE b.site_id = :site_id
          AND b.status = 'ready' AND a.status = 'ready'
          AND b.resource_type = 'image' AND a.resource_type = 'image'
          AND b.captured_at IS NOT NULL AND a.captured_at IS NOT NULL
          AND a.captured_at - b.captured_at >= (:min_days || ' days')::interval
        ORDER BY image_similarity DESC
        LIMIT :top_n
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            {"site_id": str(site_id), "min_days": MIN_DAYS_APART, "top_n": TOP_N},
        ).mappings().all()

    return [
        PairCandidate(
            before_id=UUID(str(r["before_id"])),
            after_id=UUID(str(r["after_id"])),
            image_similarity=float(r["image_similarity"]),
            days_apart=int(r["days_apart"]),
        )
        for r in rows
    ]
