from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import get_engine
from app.main import app

client = TestClient(app)


def _make_project_and_site() -> tuple[str, str]:
    project = client.post("/api/projects", json={"name": f"T10 test {uuid4()}"}).json()
    site = client.post(
        f"/api/projects/{project['id']}/sites",
        json={"name": "Test site", "lat": 12.97, "lng": 77.59},
    ).json()
    return project["id"], site["id"]


def _insert_asset(conn, project_id: str, site_id: str, captured_at: datetime, embedding: list[float]) -> str:
    asset_id = str(uuid4())
    public_id = f"pairtest_{asset_id}"
    conn.execute(
        text(
            """
            INSERT INTO assets (
                id, project_id, site_id, cld_public_id, cld_asset_id, cld_version,
                resource_type, secure_url, captured_at, captured_at_source, status
            ) VALUES (
                :id, :project_id, :site_id, :public_id, :public_id, 1,
                'image', :secure_url, :captured_at, 'exif', 'ready'
            )
            """
        ),
        {
            "id": asset_id,
            "project_id": project_id,
            "site_id": site_id,
            "public_id": public_id,
            "secure_url": f"https://example.test/{public_id}.jpg",
            "captured_at": captured_at,
        },
    )
    vec = "[" + ",".join(str(v) for v in embedding) + "]"
    conn.execute(
        text(
            "INSERT INTO asset_embeddings (asset_id, frame_s, embedding, model) "
            "VALUES (:id, 0, CAST(:vec AS vector(512)), 'test')"
        ),
        {"id": asset_id, "vec": vec},
    )
    return asset_id


def _cleanup(project_id: str, asset_ids: list[str]) -> None:
    engine = get_engine()
    assert engine is not None
    with engine.begin() as conn:
        for asset_id in asset_ids:
            conn.execute(text("DELETE FROM asset_embeddings WHERE asset_id = :id"), {"id": asset_id})
            conn.execute(text("DELETE FROM assets WHERE id = :id"), {"id": asset_id})
        conn.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})


def test_pair_suggestions_returns_one_pair_for_two_ready_assets():
    project_id, site_id = _make_project_and_site()
    now = datetime.now(UTC)
    embedding = [0.1] * 512

    engine = get_engine()
    assert engine is not None
    with engine.begin() as conn:
        before_id = _insert_asset(conn, project_id, site_id, now - timedelta(days=10), embedding)
        after_id = _insert_asset(conn, project_id, site_id, now, embedding)

    try:
        res = client.get(f"/api/sites/{site_id}/pair-suggestions")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        pair = items[0]
        assert pair["before"]["id"] == before_id
        assert pair["after"]["id"] == after_id
        assert pair["days_apart"] == 10
        assert pair["image_similarity"] > 0.99
        assert pair["framing_warning"] is False
    finally:
        _cleanup(project_id, [before_id, after_id])


def test_pair_suggestions_empty_for_unknown_site_assets():
    project_id, site_id = _make_project_and_site()
    try:
        res = client.get(f"/api/sites/{site_id}/pair-suggestions")
        assert res.status_code == 200
        assert res.json()["items"] == []
    finally:
        _cleanup(project_id, [])
