"""Minimal FastAPI application foundation for Naadi."""

from fastapi import FastAPI

from backend.app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Naadi",
    description="Emergency call-taker copilot backend foundation",
    version=settings.app_version,
)


@app.get("/")
def metadata() -> dict[str, str]:
    """Return safe application metadata."""

    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "ok",
    }


@app.get("/health")
def health() -> dict[str, object]:
    """Return process health and non-secret configuration status."""

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "gnani_api_key_configured": settings.has_gnani_api_key,
        "prisma_model": settings.gnani_model,
    }
