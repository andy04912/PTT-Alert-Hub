from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, update

from app.dependencies import CurrentUser, DbSession
from app.models import ArticleMatch, PushSubscription, utc_now
from app.schemas import (
    ActionResponse,
    PushActionResponse,
    PushStatusRead,
    PushSubscriptionCreate,
    PushSubscriptionRead,
    PushSubscriptionRemove,
)
from app.services.web_push import web_push_service

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/status", response_model=PushStatusRead)
def get_push_status(db: DbSession, current_user: CurrentUser) -> PushStatusRead:
    subscription_count = (
        db.scalar(
            select(func.count(PushSubscription.id)).where(
                PushSubscription.user_id == current_user.id
            )
        )
        or 0
    )
    enabled_subscription_count = (
        db.scalar(
            select(func.count(PushSubscription.id)).where(
                PushSubscription.user_id == current_user.id,
                PushSubscription.enabled.is_(True),
            )
        )
        or 0
    )
    return PushStatusRead(
        configured=web_push_service.configured,
        public_key=(
            web_push_service.settings.vapid_public_key
            if web_push_service.configured
            else None
        ),
        subscription_count=subscription_count,
        enabled_subscription_count=enabled_subscription_count,
    )


@router.get("/subscriptions", response_model=list[PushSubscriptionRead])
def list_push_subscriptions(
    db: DbSession,
    current_user: CurrentUser,
) -> list[PushSubscription]:
    return list(
        db.scalars(
            select(PushSubscription)
            .where(PushSubscription.user_id == current_user.id)
            .order_by(PushSubscription.updated_at.desc(), PushSubscription.id.desc())
        ).all()
    )


@router.post("/subscriptions", response_model=PushSubscriptionRead)
def save_push_subscription(
    payload: PushSubscriptionCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> PushSubscription:
    if not web_push_service.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="系統尚未完成 Web Push VAPID 設定",
        )
    if not payload.endpoint.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Push Endpoint 必須使用 HTTPS",
        )

    active_before = (
        db.scalar(
            select(func.count(PushSubscription.id)).where(
                PushSubscription.user_id == current_user.id,
                PushSubscription.enabled.is_(True),
            )
        )
        or 0
    )
    subscription = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint)
    )
    if subscription is None:
        subscription = PushSubscription(
            user_id=current_user.id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
            device_name=payload.device_name,
            user_agent=payload.user_agent,
            enabled=True,
        )
    else:
        subscription.user_id = current_user.id
        subscription.p256dh = payload.keys.p256dh
        subscription.auth = payload.keys.auth
        subscription.device_name = payload.device_name
        subscription.user_agent = payload.user_agent
        subscription.enabled = True
        subscription.failure_count = 0
        subscription.last_failure_at = None

    db.add(subscription)

    if active_before == 0:
        db.execute(
            update(ArticleMatch)
            .where(
                ArticleMatch.user_id == current_user.id,
                ArticleMatch.push_notified_at.is_(None),
            )
            .values(push_notified_at=utc_now())
        )

    db.commit()
    db.refresh(subscription)
    return subscription


@router.post("/subscriptions/remove", response_model=ActionResponse)
def remove_push_subscription(
    payload: PushSubscriptionRemove,
    db: DbSession,
    current_user: CurrentUser,
) -> ActionResponse:
    subscription = db.scalar(
        select(PushSubscription).where(
            PushSubscription.user_id == current_user.id,
            PushSubscription.endpoint == payload.endpoint,
        )
    )
    if subscription is not None:
        db.delete(subscription)
        db.commit()
    return ActionResponse(success=True, message="此裝置的推播訂閱已停用")


@router.post("/test", response_model=PushActionResponse)
def test_push_notification(
    db: DbSession,
    current_user: CurrentUser,
) -> PushActionResponse:
    if not web_push_service.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="系統尚未完成 Web Push VAPID 設定",
        )

    active_count = (
        db.scalar(
            select(func.count(PushSubscription.id)).where(
                PushSubscription.user_id == current_user.id,
                PushSubscription.enabled.is_(True),
            )
        )
        or 0
    )
    if active_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="這個帳號尚未啟用任何推播裝置",
        )

    result = web_push_service.send_test(db, current_user.id)
    if result.delivered == 0:
        detail = result.errors[0] if result.errors else "測試推播未能送達任何裝置"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    return PushActionResponse(
        success=True,
        message=f"測試推播已送達 {result.delivered} 台裝置",
        delivered=result.delivered,
        disabled=result.disabled,
        failed=result.failed,
    )
