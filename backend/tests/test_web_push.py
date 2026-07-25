from types import SimpleNamespace

from pywebpush import WebPushException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import PushSubscription
from app.services.account_service import create_user
from app.services.web_push import PendingPushArticle, WebPushService


def create_test_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def configure_service(service: WebPushService, monkeypatch) -> None:
    monkeypatch.setattr(service.settings, "vapid_public_key", "test-public-key")
    monkeypatch.setattr(service.settings, "vapid_private_key", "test-private-key")
    monkeypatch.setattr(service.settings, "vapid_subject", "mailto:test@example.com")


def create_subscription(db: Session) -> PushSubscription:
    user = create_user(
        db,
        email="push@example.com",
        display_name="Push User",
        password="strong-password-123",
    )
    subscription = PushSubscription(
        user_id=user.id,
        endpoint="https://push.example.com/subscription/123",
        p256dh="p256dh-key-value-that-is-long-enough",
        auth="auth-key-value",
        device_name="測試裝置",
        user_agent="pytest",
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def test_single_article_payload_opens_original_article() -> None:
    payload = WebPushService._build_match_payload(
        7,
        [
            PendingPushArticle(
                article_id=10,
                board="Tech_Job",
                title="[徵才] React Engineer",
                url="https://www.ptt.cc/bbs/Tech_Job/M.123.html",
                run_id=88,
            )
        ],
    )

    assert payload["url"] == "https://www.ptt.cc/bbs/Tech_Job/M.123.html"
    assert payload["tag"] == "ptt-alert-88-7"
    assert "Tech_Job" in str(payload["body"])


def test_multiple_article_payload_opens_match_history() -> None:
    payload = WebPushService._build_match_payload(
        9,
        [
            PendingPushArticle(
                article_id=10,
                board="Tech_Job",
                title="First",
                url="https://www.ptt.cc/first",
                run_id=99,
            ),
            PendingPushArticle(
                article_id=11,
                board="Soft_Job",
                title="Second",
                url="https://www.ptt.cc/second",
                run_id=99,
            ),
        ],
    )

    assert payload["url"] == "/matches"
    assert payload["count"] == 2
    assert "2 篇" in str(payload["body"])


def test_successful_delivery_updates_subscription(monkeypatch) -> None:
    engine = create_test_engine()
    service = WebPushService()
    configure_service(service, monkeypatch)
    monkeypatch.setattr("app.services.web_push.webpush", lambda **_kwargs: None)

    with Session(engine) as db:
        subscription = create_subscription(db)
        result = service._send_to_subscriptions(
            db,
            [subscription],
            {"title": "Test", "body": "Delivered", "url": "/push"},
        )
        db.commit()
        db.refresh(subscription)

        assert result.delivered == 1
        assert result.failed == 0
        assert subscription.failure_count == 0
        assert subscription.last_success_at is not None
        assert subscription.last_failure_at is None


def test_expired_endpoint_is_disabled(monkeypatch) -> None:
    engine = create_test_engine()
    service = WebPushService()
    configure_service(service, monkeypatch)

    def raise_expired(**_kwargs):
        response = SimpleNamespace(status_code=410)
        raise WebPushException("expired", response=response)

    monkeypatch.setattr("app.services.web_push.webpush", raise_expired)

    with Session(engine) as db:
        subscription = create_subscription(db)
        result = service._send_to_subscriptions(
            db,
            [subscription],
            {"title": "Test", "body": "Expired", "url": "/push"},
        )
        db.commit()
        db.refresh(subscription)

        assert result.delivered == 0
        assert result.disabled == 1
        assert subscription.enabled is False
        assert subscription.failure_count == 1
        assert subscription.last_failure_at is not None
