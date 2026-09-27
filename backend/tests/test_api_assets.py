from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import get_engine
from app.main import app

client = TestClient(app)


def _make_project() -> str:
    res = client.post("/api/projects", json={"name": f"T04 test {uuid4()}"})
    assert res.status_code == 201
    return res.json()["id"]


def _cleanup(project_id: str, asset_ids: list[str]) -> None:
    engine = get_engine()
    assert engine is not None
    with engine.begin() as conn:
        for asset_id in asset_ids:
            conn.execute(text("DELETE FROM asset_tags WHERE asset_id = :id"), {"id": asset_id})
            conn.execute(text("DELETE FROM asset_embeddings WHERE asset_id = :id"), {"id": asset_id})
            conn.execute(text("DELETE FROM assets WHERE id = :id"), {"id": asset_id})
        conn.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})


def _register(project_id: str, public_id: str) -> dict:
    res = client.post(
        "/api/assets/register",
        json={
            "project_id": project_id,
            "cld_public_id": public_id,
            "cld_asset_id": f"asset_{public_id}",
            "cld_version": 1,
            "secure_url": f"https://example.test/{public_id}.jpg",
            "resource_type": "image",
        },
    )
    return res


def test_register_list_get_and_tags_do_not_crash():
    project_id = _make_project()
    public_id = f"test_{uuid4()}"
    res = _register(project_id, public_id)
    assert res.status_code == 202
    body = res.json()
    asset_id = body["asset_id"]
    assert body["status"] == "pending"
    assert body["job_id"] is not None

    try:
        # regression: asset_tags.asset_id is uuid; ANY() needs an explicit cast, not text[]
        res = client.get(f"/api/assets/{asset_id}")
        assert res.status_code == 200
        assert res.json()["tags"] == []

        res = client.get(f"/api/assets?project_id={project_id}")
        assert res.status_code == 200
        assert len(res.json()["items"]) == 1
    finally:
        _cleanup(project_id, [asset_id])


def test_register_is_idempotent_on_public_id():
    project_id = _make_project()
    public_id = f"test_{uuid4()}"
    first = _register(project_id, public_id).json()
    second = _register(project_id, public_id)
    assert second.status_code == 200
    body = second.json()
    assert body["asset_id"] == first["asset_id"]
    assert body["job_id"] is None
    _cleanup(project_id, [first["asset_id"]])


def test_patch_asset_manual_location_and_tags():
    project_id = _make_project()
    public_id = f"test_{uuid4()}"
    asset_id = _register(project_id, public_id).json()["asset_id"]
    try:
        res = client.patch(
            f"/api/assets/{asset_id}",
            json={"lat": 12.97, "lng": 77.59, "add_tags": ["Green Cover"]},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["location_source"] == "manual"
        assert body["lat_r"] == 12.97
        assert any(t["tag"] == "green cover" and t["source"] == "manual" for t in body["tags"])

        res = client.patch(f"/api/assets/{asset_id}", json={"remove_tags": ["green cover"]})
        assert res.status_code == 200
        assert not any(t["tag"] == "green cover" for t in res.json()["tags"])
    finally:
        _cleanup(project_id, [asset_id])


def test_reprocess_unknown_asset_404():
    res = client.post(f"/api/assets/{uuid4()}/reprocess")
    assert res.status_code == 404
