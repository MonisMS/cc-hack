from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import check_database

app = FastAPI(title="FieldProof API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clip_models_downloaded() -> bool:
    return settings.models_dir.exists() and any(settings.models_dir.rglob("*.onnx"))


# Plain `def` (not async): runs in the threadpool, so a slow DB wake-up can't block the server.
@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "database": check_database(),
        "cloudinary_configured": bool(settings.cloudinary_url),
        "clip_models_downloaded": _clip_models_downloaded(),
    }
