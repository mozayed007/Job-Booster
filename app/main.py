"""Main FastAPI application for Job_Booster."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.analytics_routes import router as analytics_router
from app.api.auth_routes import router as auth_router
from app.api.dashboard_routes import router as dashboard_router
from app.api.discovery_routes import router as discovery_router
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

app = FastAPI(
    title="Job_Booster API",
    description="AI-powered startup job scanner and resume tailoring platform",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
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
        host=getattr(settings, "HOST", "0.0.0.0"),
        port=getattr(settings, "PORT", 8000),
        reload=getattr(settings, "DEBUG", True),
    )
