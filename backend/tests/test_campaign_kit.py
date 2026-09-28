from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import get_engine
from app.fieldproof import cloudinary_gw, pipelines
from app.main import app

client = TestClient(app)


def _make_project_and_site() -> tuple[str, str]:
    project = client.post("/api/projects", json={"name": f"T15 test {uuid4()}"}).json()
    site = client.post(
        f"/api/projects/{project['id']}/sites",
        json={"name": "Test site", "lat": 12.97, "lng": 77.59},
    ).json()
    return project["id"], site["id"]


def _insert_asset(conn, project_id: str, site_id: str, captured_at: datetime, tag: str) -> str:
    asset_id = str(uuid4())
    public_id = f"kittest_{asset_id}"
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
    conn.execute(
        text("INSERT INTO asset_tags (asset_id, tag, source, score, rank) VALUES (:id, :tag, 'clip', 0.9, 1)"),
        {"id": asset_id, "tag": tag},
    )
    return asset_id


def _insert_ready_comparison(conn, site_id: str, before_id: str, after_id: str) -> str:
    comparison_id = str(uuid4())
    conn.execute(
        text(
            """
            INSERT INTO comparisons (
                id, site_id, before_asset_id, after_asset_id,
                image_similarity, framing_warning, delta_green_pct_rounded, status
            ) VALUES (:id, :site_id, :before_id, :after_id, 0.95, false, 15, 'ready')
            """
        ),
        {"id": comparison_id, "site_id": site_id, "before_id": before_id, "after_id": after_id},
    )
    return comparison_id


def _cleanup(project_id: str, asset_ids: list[str], comparison_ids: list[str], report_ids: list[str]) -> None:
    engine = get_engine()
    assert engine is not None
    with engine.begin() as conn:
        for report_id in report_ids:
            conn.execute(text("DELETE FROM lineage WHERE entity_type = 'kit' AND entity_id = :id"), {"id": report_id})
            conn.execute(text("DELETE FROM lineage WHERE entity_type = 'report' AND entity_id = :id"), {"id": report_id})
            conn.execute(text("DELETE FROM report_items WHERE report_id = :id"), {"id": report_id})
            conn.execute(text("DELETE FROM reports WHERE id = :id"), {"id": report_id})
        for comparison_id in comparison_ids:
            conn.execute(text("DELETE FROM comparisons WHERE id = :id"), {"id": comparison_id})
        for asset_id in asset_ids:
            conn.execute(text("DELETE FROM asset_tags WHERE asset_id = :id"), {"id": asset_id})
            conn.execute(text("DELETE FROM assets WHERE id = :id"), {"id": asset_id})
        conn.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})


def test_campaign_kit_urls_open_and_lineage_recorded_once(monkeypatch):
    monkeypatch.setattr(cloudinary_gw, "cached_usage", lambda: None)  # skip the real credit guard call

    project_id, site_id = _make_project_and_site()
    now = datetime.now(UTC)
    engine = get_engine()
    assert engine is not None

    with engine.begin() as conn:
        before_id = _insert_asset(conn, project_id, site_id, now - timedelta(days=10), "solar panels")
        after_id = _insert_asset(conn, project_id, site_id, now, "solar panels")
        comparison_id = _insert_ready_comparison(conn, site_id, before_id, after_id)

    report = client.post(
        "/api/reports",
        json={
            "project_id": project_id,
            "date_from": (now - timedelta(days=30)).date().isoformat(),
            "date_to": (now + timedelta(days=1)).date().isoformat(),
            "comparison_ids": [comparison_id],
        },
    ).json()
    report_id = report["report_id"]

    try:
        pipelines.generate_report({"report_id": report_id, "comparison_ids": [comparison_id]})

        res = client.get(f"/api/reports/{report_id}/campaign-kit")
        assert res.status_code == 200
        items = res.json()["items"]
        kinds = {item["kind"] for item in items}
        assert "collage" in kinds
        assert "social_square" in kinds
        assert "social_story" in kinds
        for item in items:
            assert item["url"].startswith("https://")
            assert item["source_asset_ids"]

        lineage_res = client.get("/api/lineage", params={"entity_type": "kit", "entity_id": report_id})
        assert lineage_res.status_code == 200
        assert len(lineage_res.json()["items"]) == len(items)

        # a second call must not duplicate lineage rows
        client.get(f"/api/reports/{report_id}/campaign-kit")
        lineage_res_2 = client.get("/api/lineage", params={"entity_type": "kit", "entity_id": report_id})
        assert len(lineage_res_2.json()["items"]) == len(items)
    finally:
        _cleanup(project_id, [before_id, after_id], [comparison_id], [report_id])


def test_campaign_kit_blocked_by_credit_guard(monkeypatch):
    monkeypatch.setattr(
        cloudinary_gw,
        "cached_usage",
        lambda: {"credits": {"usage": 24.0, "limit": 25.0, "used_percent": 96.0}},
    )

    project_id, _site_id = _make_project_and_site()
    engine = get_engine()
    assert engine is not None
    report_id = str(uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO reports (id, project_id, date_from, date_to, status)
                VALUES (:id, :project_id, '2026-01-01', '2026-01-31', 'ready')
                """
            ),
            {"id": report_id, "project_id": project_id},
        )

    try:
        res = client.get(f"/api/reports/{report_id}/campaign-kit")
        assert res.status_code == 503
        assert res.json()["error"]["code"] == "CREDIT_GUARD"
    finally:
        _cleanup(project_id, [], [], [report_id])


def test_lineage_rejects_unknown_entity_type():
    res = client.get("/api/lineage", params={"entity_type": "bogus", "entity_id": str(uuid4())})
    assert res.status_code == 422
