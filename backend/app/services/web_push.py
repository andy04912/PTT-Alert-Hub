from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from uuid import uuid4

from pywebpush import WebPushException, webpush
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ArticleMatch, PushSubscription, Rule, SeenArticle, User, utc_now


@dataclass(slots=True)
class PushDeliveryResult:
    delivered: int = 0
    disabled: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def sent(self) -> bool:
        return self.delivered > 0

    def merge(self, other: "PushDeliveryResult") -> None:
        self.delivered += other.delivered
        self.disabled += other.disabled
        self.failed += other.failed
        self.errors.extend(other.errors)


@dataclass(slots=True)
class PendingPushArticle:
    article_id: int
    board: str
    title: str
    url: str
    rule_names: list[str] = field(default_factory=list)
    match_ids: list[int] = field(default_factory=list)
    run_id: int = 0


class WebPushService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return self.settings.web_push_configured

    def send_test(self, db: Session, user_id: int) -> PushDeliveryResult:
        subscriptions = self._active_subscriptions(db, user_id)
        payload = {
            "title": "PTT Alert Hub 測試通知",
            "body": "這台裝置已成功連結 PWA 推播。",
            "url": "/push",
            "tag": f"ptt-alert-test-{uuid4().hex}",
        }
        result = self._send_to_subscriptions(db, subscriptions, payload)
        db.commit()
        return result

    def send_pending(self, db: Session, notification_enabled: bool) -> PushDeliveryResult:
        result = PushDeliveryResult()
        if not notification_enabled:
            return result

        subscriptions = list(
            db.scalars(
                select(PushSubscription)
                .join(User, User.id == PushSubscription.user_id)
                .where(
                    PushSubscription.enabled.is_(True),
                    User.is_active.is_(True),
                )
                .order_by(PushSubscription.user_id, PushSubscription.id)
            ).all()
        )
        if not subscriptions:
            return result

        if not self.configured:
            result.failed = len(subscriptions)
            result.errors.append("Web Push 已有啟用裝置，但尚未完整設定 VAPID 金鑰。")
            return result

        subscriptions_by_user: dict[int, list[PushSubscription]] = defaultdict(list)
        for subscription in subscriptions:
            subscriptions_by_user[subscription.user_id].append(subscription)

        for user_id, user_subscriptions in subscriptions_by_user.items():
            pending_rows = db.execute(
                select(ArticleMatch, Rule, SeenArticle)
                .join(Rule, Rule.id == ArticleMatch.rule_id)
                .join(SeenArticle, SeenArticle.id == ArticleMatch.article_id)
                .where(
                    ArticleMatch.user_id == user_id,
                    ArticleMatch.push_notified_at.is_(None),
                    Rule.enabled.is_(True),
                )
                .order_by(ArticleMatch.matched_at.asc(), ArticleMatch.id.asc())
            ).all()
            if not pending_rows:
                continue

            articles = self._group_articles(pending_rows)
            payload = self._build_match_payload(user_id, articles)
            user_result = self._send_to_subscriptions(db, user_subscriptions, payload)
            result.merge(user_result)

            if user_result.delivered > 0:
                match_ids = [match_id for article in articles for match_id in article.match_ids]
                db.execute(
                    update(ArticleMatch)
                    .where(ArticleMatch.id.in_(match_ids))
                    .values(push_notified_at=utc_now())
                )

        db.commit()
        return result

    def _send_to_subscriptions(
        self,
        db: Session,
        subscriptions: list[PushSubscription],
        payload: dict[str, object],
    ) -> PushDeliveryResult:
        result = PushDeliveryResult()
        if not subscriptions:
            return result
        if not self.configured:
            result.failed = len(subscriptions)
            result.errors.append("尚未設定 VAPID 公私鑰與 Subject。")
            return result

        serialized_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {
                            "p256dh": subscription.p256dh,
                            "auth": subscription.auth,
                        },
                    },
                    data=serialized_payload,
                    vapid_private_key=self.settings.vapid_private_key,
                    vapid_claims={"sub": self.settings.vapid_subject},
                    ttl=300,
                    timeout=15,
                )
            except WebPushException as error:
                status_code = error.response.status_code if error.response is not None else None
                subscription.failure_count += 1
                subscription.last_failure_at = utc_now()
                if status_code in {404, 410}:
                    subscription.enabled = False
                    result.disabled += 1
                else:
                    result.failed += 1
                    result.errors.append(
                        f"{subscription.device_name} 推播失敗"
                        + (f"（HTTP {status_code}）" if status_code else "")
                    )
                db.add(subscription)
            except Exception:
                subscription.failure_count += 1
                subscription.last_failure_at = utc_now()
                result.failed += 1
                result.errors.append(f"{subscription.device_name} 推播處理失敗")
                db.add(subscription)
            else:
                subscription.failure_count = 0
                subscription.last_success_at = utc_now()
                subscription.last_failure_at = None
                result.delivered += 1
                db.add(subscription)

        return result

    @staticmethod
    def _active_subscriptions(db: Session, user_id: int) -> list[PushSubscription]:
        return list(
            db.scalars(
                select(PushSubscription)
                .where(
                    PushSubscription.user_id == user_id,
                    PushSubscription.enabled.is_(True),
                )
                .order_by(PushSubscription.id)
            ).all()
        )

    @staticmethod
    def _group_articles(rows) -> list[PendingPushArticle]:
        grouped: dict[int, PendingPushArticle] = {}
        for article_match, rule, article in rows:
            item = grouped.get(article.id)
            if item is None:
                item = PendingPushArticle(
                    article_id=article.id,
                    board=article.board,
                    title=article.title,
                    url=article.url,
                    run_id=article_match.run_id,
                )
                grouped[article.id] = item
            if rule.name not in item.rule_names:
                item.rule_names.append(rule.name)
            item.match_ids.append(article_match.id)
        return list(grouped.values())

    @staticmethod
    def _build_match_payload(
        user_id: int,
        articles: list[PendingPushArticle],
    ) -> dict[str, object]:
        first = articles[0]
        if len(articles) == 1:
            body = f"【{first.board}】{first.title}"
            url = first.url
        else:
            body = f"{len(articles)} 篇新文章符合規則\n【{first.board}】{first.title}"
            url = "/matches"

        return {
            "title": "PTT Alert Hub",
            "body": body[:240],
            "url": url,
            "tag": f"ptt-alert-{first.run_id}-{user_id}",
            "count": len(articles),
        }


web_push_service = WebPushService()
