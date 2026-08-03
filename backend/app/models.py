from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RuleMatchType(str, enum.Enum):
    TITLE_KEYWORD = "title_keyword"
    AUTHOR = "author"


class RuleConditionOperator(str, enum.Enum):
    TITLE_CONTAINS = "title_contains"
    TITLE_NOT_CONTAINS = "title_not_contains"


class CrawlRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    board: Mapped[str] = mapped_column(String(60), index=True)
    match_type: Mapped[RuleMatchType] = mapped_column(Enum(RuleMatchType))
    pattern: Mapped[str] = mapped_column(String(200))
    additional_conditions: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    pages_per_board: Mapped[int] = mapped_column(Integer, default=1)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class RuntimeLock(Base):
    __tablename__ = "runtime_locks"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner: Mapped[str] = mapped_column(String(100), index=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class WorkerState(Base):
    __tablename__ = "worker_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    worker_id: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class SeenArticle(Base):
    __tablename__ = "seen_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    board: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(700))
    ptt_date: Mapped[str] = mapped_column(String(20), default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(30), default="scheduler")
    status: Mapped[CrawlRunStatus] = mapped_column(Enum(CrawlRunStatus))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    boards_count: Mapped[int] = mapped_column(Integer, default=0)
    articles_scanned: Mapped[int] = mapped_column(Integer, default=0)
    matches_count: Mapped[int] = mapped_column(Integer, default=0)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class BoardCrawlSnapshot(Base):
    __tablename__ = "board_crawl_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id", ondelete="CASCADE"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    articles_count: Mapped[int] = mapped_column(Integer, default=0)
    articles: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class ArticleMatch(Base):
    __tablename__ = "article_matches"
    __table_args__ = (UniqueConstraint("rule_id", "article_id", name="uq_rule_article"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id", ondelete="CASCADE"))
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id", ondelete="CASCADE"))
    article_id: Mapped[int] = mapped_column(ForeignKey("seen_articles.id", ondelete="CASCADE"))
    matched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    push_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(String(1200), unique=True, index=True)
    p256dh: Mapped[str] = mapped_column(String(300))
    auth: Mapped[str] = mapped_column(String(200))
    device_name: Mapped[str] = mapped_column(String(100), default="瀏覽器裝置")
    user_agent: Mapped[str] = mapped_column(String(600), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
