from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, boards, crawl, dashboard, rules, settings
from app.core.config import get_settings
from app.database import SessionLocal, initialize_database
from app.services.account_service import ensure_bootstrap_admin
from app.services.app_settings import get_or_create_app_settings

app_settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    db = SessionLocal()
    try:
        ensure_bootstrap_admin(db)
        get_or_create_app_settings(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=app_settings.app_name,
    version="0.5.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(rules.router)
app.include_router(boards.router)
app.include_router(settings.router)
app.include_router(crawl.router)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "api"}
