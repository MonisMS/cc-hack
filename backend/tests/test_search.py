import pytest
from sqlalchemy import text

from app.core.db import get_engine
from app.fieldproof.schemas import SearchRequest
from app.fieldproof.search import search


def _has_ready_assets() -> bool:
    engine = get_engine()
    if engine is None:
        return False
    with engine.connect() as conn:
        return conn.execute(text("SELECT 1 FROM assets WHERE status = 'ready' LIMIT 1")).first() is not None


pytestmark = pytest.mark.integration


@pytest.mark.skipif(not _has_ready_assets(), reason="no ready assets in the DB")
def test_search_solar_panels_in_top_3():
    hits = search(SearchRequest(query="solar panels on a field", limit=10))
    top3_ids = [h.asset_id for h in hits[:3]]
    assert top3_ids, "expected at least one hit"

    engine = get_engine()
    with engine.connect() as conn:
        tags = conn.execute(
            text(
                "SELECT DISTINCT tag FROM asset_tags WHERE asset_id = ANY(CAST(:ids AS uuid[])) AND source = 'clip'"
            ),
            {"ids": [str(i) for i in top3_ids]},
        ).scalars().all()
    assert "solar" in tags


@pytest.mark.skipif(not _has_ready_assets(), reason="no ready assets in the DB")
def test_search_kids_studying_in_top_3():
    hits = search(SearchRequest(query="kids studying", limit=10))
    top3_ids = [h.asset_id for h in hits[:3]]
    assert top3_ids, "expected at least one hit"

    engine = get_engine()
    with engine.connect() as conn:
        tags = conn.execute(
            text(
                "SELECT DISTINCT tag FROM asset_tags WHERE asset_id = ANY(CAST(:ids AS uuid[])) AND source = 'clip'"
            ),
            {"ids": [str(i) for i in top3_ids]},
        ).scalars().all()
    assert "classroom" in tags


@pytest.mark.skipif(not _has_ready_assets(), reason="no ready assets in the DB")
def test_search_empty_query_is_browse_mode_ordered_by_recency():
    hits = search(SearchRequest(query="", limit=5))
    assert all(h.score == 0.0 for h in hits)
