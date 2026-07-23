from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AppSetting


def get_or_create_app_settings(db: Session) -> AppSetting:
    app_setting = db.get(AppSetting, 1)
    if app_setting is not None:
        return app_setting

    app_setting = AppSetting(id=1)
    db.add(app_setting)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_setting = db.get(AppSetting, 1)
        if existing_setting is None:
            raise
        return existing_setting

    db.refresh(app_setting)
    return app_setting
