from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import get_engine
from app.main import app

client = TestClient(app)


def _cleanup_project(project_id: str) -> None:
    engine = get_engine()
    assert engine is not None
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sites WHERE project_id = :id"), {"id": project_id})
        conn.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})


def test_create_project_and_site_with_counts():
    res = client.post("/api/projects", json={"name": "Test Project T03", "description": "d"})
    assert res.status_code == 201
    project = res.json()
    project_id = project["id"]
    try:
        assert project["asset_count"] == 0
        assert project["site_count"] == 0

        res = client.post(
            f"/api/projects/{project_id}/sites",
            json={"name": "Site A", "lat": 12.97, "lng": 77.59, "radius_m": 300},
        )
        assert res.status_code == 201
        site = res.json()
        assert site["project_id"] == project_id
        assert site["asset_count"] == 0

        res = client.get(f"/api/projects/{project_id}/sites")
        assert res.status_code == 200
        assert len(res.json()["items"]) == 1

        res = client.get(f"/api/projects/{project_id}")
        assert res.status_code == 200
        assert res.json()["site_count"] == 1

        res = client.patch(f"/api/sites/{site['id']}", json={"radius_m": 500})
        assert res.status_code == 200
        assert res.json()["radius_m"] == 500
    finally:
        _cleanup_project(project_id)


def test_unknown_project_returns_404_envelope():
    res = client.get(f"/api/projects/{uuid4()}")
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_invalid_lat_returns_422_envelope():
    res = client.post("/api/projects", json={"name": "Test Project T03 validation"})
    project_id = res.json()["id"]
    try:
        res = client.post(
            f"/api/projects/{project_id}/sites",
            json={"name": "Bad site", "lat": 999, "lng": 77.59},
        )
        assert res.status_code == 422
        body = res.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
    finally:
        _cleanup_project(project_id)
