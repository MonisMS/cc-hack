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
    openrouter_api_key: str | None = None

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # The web app is deployed on Vercel (production + preview URLs).
    cors_origin_regex: str | None = r"https://[a-z0-9-]+\.vercel\.app"
    models_dir: Path = BACKEND_DIR / "models"

    gemini_model: str = "gemini/gemini-3.5-flash-lite"
    # Free OpenRouter models that support structured JSON output (checked 29 Sep 2026).
    openrouter_models: list[str] = [
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        "openrouter/google/gemma-4-31b-it:free",
    ]
    cloudinary_image_preset: str = "fp_image"
    enable_g_auto: bool = True
    enable_blur_faces: bool = True
    enable_vision_descriptions: bool = False
    credit_guard_percent: int = 80
    framing_sim_threshold: float = 0.80
    green_exg_threshold: float = 0.10
    site_radius_m_default: int = 200
    demo_mode: bool = False
    hf_hub_offline: str = "0"


settings = Settings()
