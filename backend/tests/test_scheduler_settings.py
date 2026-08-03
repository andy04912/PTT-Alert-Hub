import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text

from app.database import _ensure_scheduler_columns
from app.schemas import AppSettingUpdate


def test_30_second_interval_accepts_one_page() -> None:
    setting = AppSettingUpdate(
        interval_seconds=30,
        pages_per_board=1,
        notification_enabled=True,
    )

    assert setting.interval_seconds == 30
    assert setting.pages_per_board == 1


def test_30_second_interval_rejects_multiple_pages() -> None:
    with pytest.raises(ValidationError, match="只能掃描 1 頁"):
        AppSettingUpdate(
            interval_seconds=30,
            pages_per_board=2,
            notification_enabled=True,
        )


def test_60_second_interval_accepts_two_pages() -> None:
    setting = AppSettingUpdate(
        interval_seconds=60,
        pages_per_board=2,
        notification_enabled=True,
    )

    assert setting.pages_per_board == 2


def test_interval_cannot_be_lower_than_30_seconds() -> None:
    with pytest.raises(ValidationError):
        AppSettingUpdate(
            interval_seconds=29,
            pages_per_board=1,
            notification_enabled=True,
        )


def test_legacy_minute_columns_are_migrated_to_30_seconds() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE app_settings ("
                "id INTEGER PRIMARY KEY, "
                "interval_minutes INTEGER NOT NULL DEFAULT 10, "
                "pages_per_board INTEGER NOT NULL DEFAULT 1, "
                "notification_enabled BOOLEAN NOT NULL DEFAULT 1, "
                "updated_at DATETIME"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO app_settings "
                "(id, interval_minutes, pages_per_board, notification_enabled) "
                "VALUES (1, 10, 5, 1)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE worker_state ("
                "id INTEGER PRIMARY KEY, "
                "worker_id VARCHAR(100) NOT NULL, "
                "active BOOLEAN NOT NULL DEFAULT 1, "
                "started_at DATETIME, "
                "heartbeat_at DATETIME, "
                "next_run_at DATETIME, "
                "interval_minutes INTEGER NOT NULL DEFAULT 10, "
                "updated_at DATETIME"
                ")"
            )
        )

        _ensure_scheduler_columns(connection)

        setting = connection.execute(
            text(
                "SELECT interval_seconds, pages_per_board "
                "FROM app_settings WHERE id = 1"
            )
        ).one()
        worker_columns = {
            column["name"] for column in inspect(connection).get_columns("worker_state")
        }

    assert setting.interval_seconds == 30
    assert setting.pages_per_board == 1
    assert "interval_seconds" in worker_columns
