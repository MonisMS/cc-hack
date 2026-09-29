import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.db import check_database
from app.core.errors import ApiError
from app.fieldproof.routes import router

log = logging.getLogger("fieldproof.main")


def _warm_text_model() -> None:
    try:
        from app.fieldproof import embeddings

        embeddings.embed_text("warm up")
        log.info("text embedding model warmed up")
    except Exception:
        log.exception("text embedding model warm-up failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_warm_text_model, daemon=True).start()
    yield


app = FastAPI(title="FieldProof API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def _envelope(code: str, message: str, details: object = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details if details is not None else {}}}


@app.exception_handler(ApiError)
def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=_envelope(exc.code, exc.message, exc.details))


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_envelope("VALIDATION_ERROR", "invalid request", jsonable_encoder(exc.errors())),
    )


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content=_envelope("INTERNAL", "internal server error"))


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
