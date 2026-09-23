from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

# The two CLIP models share one 512-d vector space; never mix in another model.
CLIP_VISION_MODEL = "Qdrant/clip-ViT-B-32-vision"
CLIP_TEXT_MODEL = "Qdrant/clip-ViT-B-32-text"
EMBED_DIM = 512


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Neon *direct* (non-pooler) connection string, e.g. postgresql+psycopg://...?sslmode=require
    database_url: str | None = None
    # cloudinary://<api_key>:<api_secret>@<cloud_name>
    cloudinary_url: str | None = None
    gemini_api_key: str | None = None
    cerebras_api_key: str | None = None
    groq_api_key: str | None = None

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    models_dir: Path = BACKEND_DIR / "models"


settings = Settings()
