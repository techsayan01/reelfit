from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api import (
    routes_auth,
    routes_credits,
    routes_festival_admin,
    routes_festivals,
    routes_films,
    routes_profiles,
    routes_reviews,
    routes_submissions,
)
from app.config import get_settings
from app.db import create_all

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Development convenience; production schema is managed by Alembic.
    create_all()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url="/internal/docs")
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        https_only=not settings.debug,
        same_site="lax",
    )
    # Vite dev server origin (React SPA dev mode); same-origin in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (
        routes_auth, routes_festivals, routes_films, routes_submissions,
        routes_reviews, routes_credits, routes_festival_admin, routes_profiles,
    ):
        app.include_router(module.router)

    # Serve the built React SPA when present (production / local preview).
    if FRONTEND_DIST.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(FRONTEND_DIST / "assets")),
            name="assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
