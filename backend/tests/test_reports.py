from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import get_engine
from app.fieldproof import pipelines
from app.main import app

client = TestClient(app)


def _make_project_and_site() -> tuple[str, str]:
    project = client.post("/api/projects", json={"name": f"T14 test {uuid4()}"}).json()
    site = client.post(
        f"/api/projects/{project['id']}/sites",
        json={"name": "Test site", "lat": 12.97, "lng": 77.59},
    ).json()
    return project["id"], site["id"]


def _insert_asset(conn, project_id: str, site_id: str, captured_at: datetime, tag: str) -> str:
    asset_id = str(uuid4())
    public_id = f"reporttest_{asset_id}"
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
        text(
            """
            INSERT INTO asset_tags (asset_id, tag, source, score, rank)
            VALUES (:id, :tag, 'clip', 0.9, 1)
            """
        ),
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
            ) VALUES (
                :id, :site_id, :before_id, :after_id, 0.95, false, 15, 'ready'
            )
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
            conn.execute(text("DELETE FROM report_items WHERE report_id = :id"), {"id": report_id})
            conn.execute(text("DELETE FROM lineage WHERE entity_type = 'report' AND entity_id = :id"), {"id": report_id})
            conn.execute(text("DELETE FROM reports WHERE id = :id"), {"id": report_id})
        for comparison_id in comparison_ids:
            conn.execute(text("DELETE FROM comparisons WHERE id = :id"), {"id": comparison_id})
        for asset_id in asset_ids:
            conn.execute(text("DELETE FROM asset_tags WHERE asset_id = :id"), {"id": asset_id})
            conn.execute(text("DELETE FROM assets WHERE id = :id"), {"id": asset_id})
        conn.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})


def test_report_reaches_ready_with_consistent_metrics():
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

        res = client.get(f"/api/reports/{report_id}")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ready"
        assert body["summary_model"] == "template"
        assert body["summary"]["headline"]
        assert 2 <= len(body["summary"]["paragraphs"]) <= 3
        assert 3 <= len(body["summary"]["highlights"]) <= 5

        metrics = body["metrics"]
        assert metrics["assets_total"] == 2
        assert metrics["images"] == 2
        assert metrics["sites_with_evidence"] == 1
        assert metrics["top_activities"][0]["tag"] == "solar panels"
        assert metrics["top_activities"][0]["count"] == 2
        assert metrics["comparisons"][0]["id"] == comparison_id
        assert metrics["comparisons"][0]["delta_green_pct_rounded"] == 15

        kinds = {item["kind"] for item in body["items"]}
        assert "asset" in kinds
        assert "comparison" in kinds
        comparison_items = [i for i in body["items"] if i["kind"] == "comparison"]
        assert comparison_items[0]["comparison"]["id"] == comparison_id

        list_res = client.get(f"/api/projects/{project_id}/reports")
        assert list_res.status_code == 200
        assert any(r["id"] == report_id for r in list_res.json()["items"])
    finally:
        _cleanup(project_id, [before_id, after_id], [comparison_id], [report_id])


def test_create_report_rejects_unready_comparison():
    project_id, site_id = _make_project_and_site()
    now = datetime.now(UTC)
    engine = get_engine()
    assert engine is not None

    with engine.begin() as conn:
        before_id = _insert_asset(conn, project_id, site_id, now - timedelta(days=10), "flooded road")
        after_id = _insert_asset(conn, project_id, site_id, now, "flooded road")
        pending_comparison_id = str(uuid4())
        conn.execute(
            text(
                """
                INSERT INTO comparisons (
                    id, site_id, before_asset_id, after_asset_id, status
                ) VALUES (:id, :site_id, :before_id, :after_id, 'pending')
                """
            ),
            {"id": pending_comparison_id, "site_id": site_id, "before_id": before_id, "after_id": after_id},
        )

    try:
        res = client.post(
            "/api/reports",
            json={
                "project_id": project_id,
                "date_from": (now - timedelta(days=30)).date().isoformat(),
                "date_to": (now + timedelta(days=1)).date().isoformat(),
                "comparison_ids": [pending_comparison_id],
            },
        )
        assert res.status_code == 422
    finally:
        _cleanup(project_id, [before_id, after_id], [pending_comparison_id], [])
