from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import SessionLocal
from app.models import (
    ArticleMatch,
    CrawlRun,
    CrawlRunStatus,
    Rule,
    SeenArticle,
    User,
    utc_now,
)
from app.services.app_settings import get_or_create_app_settings
from app.services.distributed_lock import distributed_lock_service
from app.services.matcher import article_matches_rule
from app.services.notifier import (
    SAFE_MESSAGE_LIMIT,
    MatchedArticle,
    NotificationError,
    TelegramNotifier,
    build_notification_message,
)
from app.services.ptt_crawler import PttArticle, PttCrawler, PttCrawlerError
from app.services.web_push import web_push_service

CRAWL_LOCK_NAME = "ptt-crawl-run"


class CrawlService:
    def __init__(self) -> None:
        self._local_lock = threading.Lock()
        self.settings = get_settings()
        self.crawler = PttCrawler()
        self.notifier = TelegramNotifier()

    @property
    def is_running(self) -> bool:
        return self._local_lock.locked()

    def run(self, trigger: str = "scheduler") -> CrawlRun:
        if not self._local_lock.acquire(blocking=False):
            return self._create_skipped_run(trigger)

        try:
            with distributed_lock_service.acquire(
                name=CRAWL_LOCK_NAME,
                ttl_seconds=self.settings.crawl_lock_ttl_seconds,
            ) as acquired:
                if not acquired:
                    return self._create_skipped_run(trigger)
                return self._run_locked(trigger)
        finally:
            self._local_lock.release()

    def _run_locked(self, trigger: str) -> CrawlRun:
        db = SessionLocal()
        run = CrawlRun(trigger=trigger, status=CrawlRunStatus.RUNNING)
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            self._execute_run(db, run)
        except Exception as error:
            db.rollback()
            run = db.get(CrawlRun, run.id) or run
            run.status = CrawlRunStatus.FAILED
            run.finished_at = utc_now()
            run.error_message = f"未預期錯誤：{error}"
            db.add(run)
            db.commit()
        finally:
            run_id = run.id
            db.close()

        result_db = SessionLocal()
        try:
            return result_db.get(CrawlRun, run_id) or run
        finally:
            result_db.close()

    def _execute_run(self, db: Session, run: CrawlRun) -> None:
        app_setting = get_or_create_app_settings(db)
        rules = list(
            db.scalars(
                select(Rule).where(Rule.enabled.is_(True)).order_by(Rule.board, Rule.id)
            ).all()
        )
        rules_by_board: dict[str, list[Rule]] = defaultdict(list)
        for rule in rules:
            rules_by_board[rule.board].append(rule)

        run.boards_count = len(rules_by_board)
        new_matched_article_ids: set[int] = set()
        errors: list[str] = []
        crawl_failed = False

        for board, board_rules in rules_by_board.items():
            try:
                articles = self.crawler.crawl_board(board, pages=app_setting.pages_per_board)
            except PttCrawlerError as error:
                crawl_failed = True
                errors.append(f"{board}：{error}")
                continue

            run.articles_scanned += len(articles)
            for article in articles:
                seen_article = db.scalar(
                    select(SeenArticle).where(SeenArticle.article_key == article.article_key)
                )
                if seen_article is not None:
                    continue

                seen_article = SeenArticle(
                    article_key=article.article_key,
                    board=article.board,
                    title=article.title,
                    author=article.author,
                    url=article.url,
                    ptt_date=article.ptt_date,
                    published_at=article.published_at,
                )
                db.add(seen_article)
                db.flush()

                article_has_match = False
                for rule in board_rules:
                    if not self._article_is_newer_than_rule(article.published_at, rule.created_at):
                        continue
                    if not article_matches_rule(article, rule):
                        continue

                    db.add(
                        ArticleMatch(
                            user_id=rule.user_id,
                            run_id=run.id,
                            rule_id=rule.id,
                            article_id=seen_article.id,
                        )
                    )
                    article_has_match = True

                if article_has_match:
                    new_matched_article_ids.add(seen_article.id)

            db.commit()

        run.matches_count = len(new_matched_article_ids)
        telegram_message, telegram_failed, telegram_sent = self._send_pending_notification(
            db,
            app_setting.notification_enabled,
        )
        if telegram_message:
            errors.append(telegram_message)

        push_result = web_push_service.send_pending(
            db,
            app_setting.notification_enabled,
        )
        if push_result.errors:
            unique_push_errors = list(dict.fromkeys(push_result.errors))
            errors.append("Web Push：" + "；".join(unique_push_errors[:5]))

        push_failed = push_result.failed > 0 and push_result.delivered == 0
        run.notification_sent = telegram_sent or push_result.sent
        run.status = (
            CrawlRunStatus.FAILED
            if telegram_failed or push_failed or crawl_failed
            else CrawlRunStatus.SUCCESS
        )
        run.error_message = "\n".join(errors) if errors else None
        run.finished_at = utc_now()
        db.add(run)
        db.commit()

    def _send_pending_notification(
        self,
        db: Session,
        notification_enabled: bool,
    ) -> tuple[str | None, bool, bool]:
        pending_matches = self._load_pending_matches(db)
        if not pending_matches:
            return None, False, False
        if not notification_enabled:
            return (
                "已有符合文章，但系統通知目前停用；命中紀錄會保留等待下次通知。",
                False,
                False,
            )
        if not self.notifier.configured:
            return "已有符合文章，但尚未設定 Telegram Bot Token 或 Chat ID。", True, False

        selected: list[MatchedArticle] = []
        for pending_match in pending_matches:
            candidate = selected + [pending_match]
            candidate_message = build_notification_message(
                candidate,
                pending_count=len(pending_matches),
            )
            if len(candidate_message) > SAFE_MESSAGE_LIMIT and selected:
                break
            selected = candidate

        message = build_notification_message(selected, pending_count=len(pending_matches))
        try:
            self.notifier.send(message)
        except NotificationError as error:
            return str(error), True, False

        notified_match_ids = [match_id for item in selected for match_id in item.match_ids]
        if notified_match_ids:
            db.execute(
                update(ArticleMatch)
                .where(ArticleMatch.id.in_(notified_match_ids))
                .values(notified_at=utc_now())
            )
            db.commit()
        return None, False, True

    @staticmethod
    def _load_pending_matches(db: Session) -> list[MatchedArticle]:
        rows = db.execute(
            select(ArticleMatch, Rule, SeenArticle)
            .join(Rule, Rule.id == ArticleMatch.rule_id)
            .join(SeenArticle, SeenArticle.id == ArticleMatch.article_id)
            .join(User, User.id == ArticleMatch.user_id)
            .where(
                ArticleMatch.notified_at.is_(None),
                Rule.enabled.is_(True),
                User.is_admin.is_(True),
                User.is_active.is_(True),
            )
            .order_by(ArticleMatch.matched_at.asc(), ArticleMatch.id.asc())
        ).all()

        grouped: dict[int, MatchedArticle] = {}
        for article_match, rule, article in rows:
            grouped_item = grouped.get(article.id)
            if grouped_item is None:
                grouped_item = MatchedArticle(
                    article=PttArticle(
                        article_key=article.article_key,
                        board=article.board,
                        title=article.title,
                        author=article.author,
                        url=article.url,
                        ptt_date=article.ptt_date,
                        published_at=article.published_at,
                    ),
                    rules=[],
                    match_ids=[],
                )
                grouped[article.id] = grouped_item
            grouped_item.rules.append(rule)
            grouped_item.match_ids.append(article_match.id)

        return list(grouped.values())

    @staticmethod
    def _article_is_newer_than_rule(
        published_at: datetime | None,
        rule_created_at: datetime,
    ) -> bool:
        if published_at is None:
            return False
        return published_at >= rule_created_at

    @staticmethod
    def _create_skipped_run(trigger: str) -> CrawlRun:
        db = SessionLocal()
        try:
            run = CrawlRun(
                trigger=trigger,
                status=CrawlRunStatus.SKIPPED,
                started_at=utc_now(),
                finished_at=utc_now(),
                error_message="已有另一個爬取工作正在執行。",
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return run
        finally:
            db.close()


crawl_service = CrawlService()
