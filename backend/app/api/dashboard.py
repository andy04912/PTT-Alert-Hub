from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import distinct, func, select

from app.core.config import get_settings
from app.dependencies import CurrentUser, DbSession
from app.models import ArticleMatch, CrawlRun, Rule, WorkerState, utc_now
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
settings = get_settings()


@router.get("", response_model=DashboardStats)
def get_dashboard(db: DbSession, current_user: CurrentUser) -> DashboardStats:
    total_rules = (
        db.scalar(
            select(func.count(Rule.id)).where(Rule.user_id == current_user.id)
        )
        or 0
    )
    enabled_rules = (
        db.scalar(
            select(func.count(Rule.id)).where(
                Rule.user_id == current_user.id,
                Rule.enabled.is_(True),
            )
        )
        or 0
    )
    seen_articles = (
        db.scalar(
            select(func.count(distinct(ArticleMatch.article_id))).where(
                ArticleMatch.user_id == current_user.id
            )
        )
        or 0
    )
    total_matches = (
        db.scalar(
            select(func.count(ArticleMatch.id)).where(
                ArticleMatch.user_id == current_user.id
            )
        )
        or 0
    )
    last_run = db.scalar(select(CrawlRun).order_by(CrawlRun.id.desc()).limit(1))
    worker_state = db.get(WorkerState, 1)

    heartbeat_deadline = utc_now() - timedelta(
        seconds=settings.worker_heartbeat_timeout_seconds
    )
    scheduler_running = bool(
        worker_state
        and worker_state.active
        and worker_state.heartbeat_at >= heartbeat_deadline
    )

    return DashboardStats(
        enabled_rules=enabled_rules,
        total_rules=total_rules,
        seen_articles=seen_articles,
        total_matches=total_matches,
        last_run=last_run,
        next_run_at=worker_state.next_run_at if scheduler_running and worker_state else None,
        scheduler_running=scheduler_running,
        telegram_configured=current_user.is_admin and settings.telegram_configured,
    )
