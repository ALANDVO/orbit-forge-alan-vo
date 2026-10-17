"""FastAPI application factory for Orbit Forge.

Creates and configures the ASGI application with:
* Database schema initialization on startup.
* CORS configured for localhost development origins.
* OpenAPI documentation (Swagger UI at ``/docs``).
* All API routers mounted under ``/api/v1``.

The app can be run directly via ``uvicorn app.main:app`` or imported
programmatically (e.g., in tests via ``TestClient``).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.evaluation import router as evaluation_router
from app.api.intents import router as intents_router
from app.core.config import Settings, get_settings
from app.core.database import init_db

VERSION = "1.0.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory: builds a configured FastAPI instance.

    Accepts an optional settings override, primarily for testing.
    """

    if settings is None:
        settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_url = settings.database_url
        init_db(db_url)
        yield

    app = FastAPI(
        title="Orbit Forge API",
        description="Deterministic Intent Graph Compiler for generative workflows.",
        version=VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(intents_router, prefix="/api/v1/intents")
    app.include_router(audit_router, prefix="/api/v1/audit")
    app.include_router(evaluation_router, prefix="/api/v1/evaluation")

    # Root and version endpoints
    @app.get("/")
    def root() -> dict[str, str]:
        return {"name": "Orbit Forge", "version": VERSION}

    @app.get("/version")
    def version() -> dict[str, str]:
        return {"version": VERSION}

    app.state.settings = settings

    return app


def _cors_origins(settings: Settings) -> list[str]:
    """Compute allowed CORS origins for the current environment."""
    origins = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    if settings.is_production():
        origins = ["https://127.0.0.1:3000", "https://localhost:3000"]
    return origins


# Module-level app instance for uvicorn: ``python -m uvicorn app.main:app``
app = create_app()