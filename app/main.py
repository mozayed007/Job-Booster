"""Main FastAPI application for Job_Booster."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.analytics_routes import router as analytics_router
from app.api.auth_routes import router as auth_router
from app.api.ax_routes import router as ax_router
from app.api.dashboard_routes import router as dashboard_router
from app.api.discovery_routes import router as discovery_router
from app.api.gap_recommendation_routes import router as gap_recommendation_router
from app.api.onboarding_routes import router as onboarding_router
from app.api.pipeline_routes import router as pipeline_router
from app.api.recommendation_routes import router as recommendation_router
from app.api.resume_routes import router as resume_router
from app.api.scanner_routes import router as scanner_router
from app.api.search_routes import router as search_router
from app.api.settings_routes import router as settings_router
from app.api.tracking_routes import router as tracking_router
from app.core.config import settings
from app.core.model_registry import get_registry, init_ai_stack
from app.services.db_service import initialize_database_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # Startup
    logger.info("Starting Job_Booster API...")
    initialize_database_tables()
    try:
        init_ai_stack()
        # Probe local providers async (Ollama, vLLM) — avoids blocking
        # the event loop with synchronous HTTP calls at import time.
        await get_registry().probe_local_providers()
    except Exception as e:
        logger.warning(f"AI stack init failed (non-fatal): {e}")
    try:
        from app.pipelines.scheduler import start_scheduler

        start_scheduler()
    except Exception as e:
        logger.warning("Scheduler start failed (non-fatal): {}", e)
    logger.info("Job_Booster API ready")
    yield
    # Shutdown
    try:
        from app.pipelines.scheduler import stop_scheduler

        stop_scheduler()
    except Exception:
        pass
    logger.info("Shutting down Job_Booster API")


logging.basicConfig(level=logging.INFO)

# CORS: ``allow_credentials=True`` combined with a wildcard origin is an
# invalid + insecure configuration (browsers reject it, and the intent to
# allow any origin with credentials is a credential-theft vector). When the
# operator has not supplied an explicit allow-list we disable credentials.
_cors_raw = settings.CORS_ORIGINS.strip()
_cors_is_wildcard = _cors_raw == "*" or _cors_raw == ""
if _cors_is_wildcard:
    _cors_origins = ["*"]
else:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app = FastAPI(
    title="Job_Booster API",
    description="AI-powered startup job scanner and resume tailoring platform",
    version="0.2.0",
    # Only expose interactive API docs in debug/development.
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Preserve client-safe 4xx detail; sanitize 5xx detail."""
    if exc.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR:
        detail = exc.detail
    else:
        detail = "Internal server error"
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


@app.exception_handler(Exception)
async def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: never leak internal exception text to clients."""
    logger.exception("Unhandled exception in {}", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not _cors_is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scanner_router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(recommendation_router, prefix="/api")
app.include_router(tracking_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")
app.include_router(discovery_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(ax_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(gap_recommendation_router, prefix="/api")


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "name": "Job_Booster API",
        "version": "0.2.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/health/models", tags=["Health"])
async def model_health_check():
    """Check which LLM providers are reachable."""
    from app.core.model_registry import get_status, health_check

    status = get_status()
    checks = await health_check()
    return {
        "status": "ok",
        "config": status,
        "providers": checks,
    }


@app.get("/health/status", tags=["Health"])
async def model_status():
    """Get model registry status (sync, no network calls)."""
    from app.core.model_registry import get_status

    return get_status()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=getattr(settings, "HOST", "127.0.0.1"),
        port=getattr(settings, "PORT", 8000),
        reload=settings.DEBUG,
    )
