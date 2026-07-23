from fastapi import APIRouter, Query
from sqlalchemy import select

from app.dependencies import AdminUser, DbSession
from app.models import CrawlRun
from app.schemas import CrawlRunRead
from app.services.crawl_service import crawl_service

router = APIRouter(prefix="/api/crawl", tags=["crawl"])


@router.post("/run", response_model=CrawlRunRead)
def run_crawl(_admin: AdminUser) -> CrawlRun:
    return crawl_service.run(trigger="manual")


@router.get("/runs", response_model=list[CrawlRunRead])
def list_runs(
    db: DbSession,
    _admin: AdminUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CrawlRun]:
    return list(db.scalars(select(CrawlRun).order_by(CrawlRun.id.desc()).limit(limit)).all())
