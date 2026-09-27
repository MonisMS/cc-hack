from datetime import datetime, timezone

import pytest

from app.core.errors import RetryableError
from app.fieldproof import cloudinary_gw


def test_admin_call_blocks_at_budget_limit_with_no_network(monkeypatch):
    monkeypatch.setattr(cloudinary_gw, "_admin_calls", [datetime.now(timezone.utc)] * 300)
    called = []

    def fn():
        called.append(1)
        return {}

    with pytest.raises(RetryableError):
        cloudinary_gw._admin_call("test", fn)
    assert called == []
