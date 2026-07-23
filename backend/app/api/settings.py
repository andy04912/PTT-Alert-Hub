from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.dependencies import AdminUser, DbSession
from app.schemas import ActionResponse, AppSettingRead, AppSettingUpdate
from app.services.app_settings import get_or_create_app_settings
from app.services.notifier import NotificationError, TelegramNotifier

router = APIRouter(prefix="/api/settings", tags=["settings"])
settings = get_settings()
notifier = TelegramNotifier()


def to_read_model(app_setting) -> AppSettingRead:
    return AppSettingRead(
        interval_minutes=app_setting.interval_minutes,
        pages_per_board=app_setting.pages_per_board,
        notification_enabled=app_setting.notification_enabled,
        telegram_configured=settings.telegram_configured,
        timezone=settings.timezone,
        updated_at=app_setting.updated_at,
    )


@router.get("", response_model=AppSettingRead)
def get_app_settings(db: DbSession, _admin: AdminUser) -> AppSettingRead:
    return to_read_model(get_or_create_app_settings(db))


@router.put("", response_model=AppSettingRead)
def update_app_settings(
    payload: AppSettingUpdate,
    db: DbSession,
    _admin: AdminUser,
) -> AppSettingRead:
    app_setting = get_or_create_app_settings(db)
    app_setting.interval_minutes = payload.interval_minutes
    app_setting.pages_per_board = payload.pages_per_board
    app_setting.notification_enabled = payload.notification_enabled
    db.add(app_setting)
    db.commit()
    db.refresh(app_setting)
    return to_read_model(app_setting)


@router.post("/test-notification", response_model=ActionResponse)
def test_notification(_admin: AdminUser) -> ActionResponse:
    try:
        notifier.send_test()
    except NotificationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    return ActionResponse(success=True, message="Telegram 測試通知已送出")
