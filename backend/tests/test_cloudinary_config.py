import cloudinary

from app.core.config import settings
from app.fieldproof import cloudinary_gw


def test_configure_sets_cloud_name_from_cloudinary_url(monkeypatch):
    monkeypatch.setattr(settings, "cloudinary_url", "cloudinary://k:s@mycloud")
    cloudinary_gw._configured = False
    try:
        cloudinary_gw._configure()
        assert cloudinary.config().cloud_name == "mycloud"
    finally:
        cloudinary_gw._configured = False
