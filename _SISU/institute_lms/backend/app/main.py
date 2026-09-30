"""Sisu Academy FastAPI application."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import academics, commerce, content, health, identity, institutions, learning
from .config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = settings or get_settings()
        runtime.validate_runtime()
        app.state.settings = runtime
        yield

    app = FastAPI(
        title="Sisu Academy API",
        version="1.0.0",
        description="FastAPI service backed by Supabase Auth and PostgreSQL",
        lifespan=lifespan,
    )

    if settings:
        origins = settings.allowed_origins
    else:
        configured = os.getenv("FRONTEND_URL", "http://127.0.0.1:5178")
        extras = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5178,http://localhost:5178")
        origins = sorted({configured.rstrip("/"), *(item.strip().rstrip("/") for item in extras.split(",") if item.strip())})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    for router in (
        health.router,
        identity.router,
        institutions.router,
        learning.router,
        academics.router,
        commerce.router,
        content.router,
    ):
        app.include_router(router, prefix="/api")

    @app.exception_handler(RuntimeError)
    async def persistence_error(_: Request, __: RuntimeError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": "The application database request failed"})

    return app


app = create_app()
