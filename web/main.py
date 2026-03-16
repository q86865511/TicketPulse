"""FastAPI Web App entry point — primary user interface."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from core.config import settings
from core.logger import get_logger, setup_logging
from db.models import Base
from db.session import engine
from web.routers import auth, history, interactions, profile, watchlist

setup_logging()
logger = get_logger(__name__)

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")
    yield
    await engine.dispose()
    logger.info("database_engine_disposed")


app = FastAPI(
    title="TicketPulse",
    description="Real-time concert ticket monitoring",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

# ──────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────
app.add_middleware(SessionMiddleware, secret_key=settings.app_secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Static files
# ──────────────────────────────────────────────
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ──────────────────────────────────────────────
# API Routers
# ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(watchlist.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(interactions.router)  # /interactions — no prefix


# ──────────────────────────────────────────────
# Web Pages (SSR via Jinja2)
# ──────────────────────────────────────────────

def _user_context(request: Request) -> dict:
    return {
        "user_id": request.session.get("user_id"),
        "username": request.session.get("username"),
        "avatar_url": request.session.get("avatar_url"),
        "base_url": settings.app_base_url,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, **_user_context(request)})


@app.get("/watchlist", response_class=HTMLResponse)
async def watchlist_page(request: Request):
    if not request.session.get("user_id"):
        return templates.TemplateResponse("index.html", {"request": request, **_user_context(request), "require_login": True})
    return templates.TemplateResponse("watchlist.html", {"request": request, **_user_context(request)})


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    if not request.session.get("user_id"):
        return templates.TemplateResponse("index.html", {"request": request, **_user_context(request), "require_login": True})
    return templates.TemplateResponse("history.html", {"request": request, **_user_context(request)})


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    if not request.session.get("user_id"):
        return templates.TemplateResponse("index.html", {"request": request, **_user_context(request), "require_login": True})
    return templates.TemplateResponse("profile.html", {"request": request, **_user_context(request)})


@app.get("/profile/{discord_id}", response_class=HTMLResponse)
async def public_profile_page(request: Request, discord_id: str):
    return templates.TemplateResponse("profile.html", {"request": request, **_user_context(request), "target_discord_id": discord_id})


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/health/scrapers")
async def health_scrapers() -> dict:
    from db.session import AsyncSessionLocal
    import db.crud as crud

    async with AsyncSessionLocal() as db:
        states = await crud.get_active_scraper_states(db)

    return {
        "active_scrapers": len(states),
        "scrapers": [
            {
                "platform": s.platform.value,
                "concert_id": s.concert_id,
                "last_checked_at": s.last_checked_at.isoformat() if s.last_checked_at else None,
                "consecutive_failures": s.consecutive_failures,
                "is_active": s.is_active,
            }
            for s in states
        ],
    }
