from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.db import get_engine


def record(
    output_kind: str,
    output_ref: str,
    sources: list[UUID] | None = None,
    tool: str | None = None,
    model: str | None = None,
    transformation: str | None = None,
    params: dict[str, Any] | None = None,
    entity: tuple[str, UUID] | None = None,
    source_public_ids: list[str] | None = None,
    source_versions: list[int] | None = None,
) -> UUID:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    lineage_id = uuid4()
    entity_type, entity_id = entity if entity else ("unknown", uuid4())
    import json

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO lineage (
                    id, entity_type, entity_id, output_kind, output_ref,
                    source_asset_ids, source_public_ids, source_versions,
                    tool, transformation, model, params
                ) VALUES (
                    :id, :entity_type, :entity_id, :output_kind, :output_ref,
                    CAST(:source_asset_ids AS uuid[]),
                    CAST(:source_public_ids AS text[]),
                    CAST(:source_versions AS integer[]),
                    :tool, :transformation, :model, CAST(:params AS jsonb)
                )
                """
            ),
            {
                "id": str(lineage_id),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "output_kind": output_kind,
                "output_ref": output_ref,
                "source_asset_ids": _pg_uuid_array(sources or []),
                "source_public_ids": _pg_text_array(source_public_ids or []),
                "source_versions": _pg_int_array(source_versions or []),
                "tool": tool,
                "transformation": transformation,
                "model": model,
                "params": json.dumps(params or {}),
            },
        )
    return lineage_id


def delete_for(entity_type: str, entity_id: UUID, output_kinds: list[str]) -> None:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    if not output_kinds:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM lineage
                WHERE entity_type = :t AND entity_id = :id
                  AND output_kind = ANY(CAST(:kinds AS text[]))
                """
            ),
            {"t": entity_type, "id": str(entity_id), "kinds": _pg_text_array(output_kinds)},
        )


def for_entity(entity_type: str, entity_id: UUID) -> list[dict[str, Any]]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT * FROM lineage
                WHERE entity_type = :t AND entity_id = :id
                ORDER BY created_at
                """
            ),
            {"t": entity_type, "id": str(entity_id)},
        ).mappings().all()
    return [dict(r) for r in rows]


def _pg_uuid_array(ids: list[UUID]) -> str:
    inner = ",".join(str(i) for i in ids)
    return "{" + inner + "}"


def _pg_text_array(items: list[str]) -> str:
    inner = ",".join(i.replace(",", " ") for i in items)
    return "{" + inner + "}"


def _pg_int_array(items: list[int]) -> str:
    inner = ",".join(str(i) for i in items)
    return "{" + inner + "}"
