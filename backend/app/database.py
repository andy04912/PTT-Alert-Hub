import sqlite3
from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    pass


def _ensure_account_columns(connection: Connection) -> None:
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    if "rules" in table_names:
        rule_columns = {column["name"] for column in inspector.get_columns("rules")}
        if "user_id" not in rule_columns:
            connection.execute(text("ALTER TABLE rules ADD COLUMN user_id INTEGER"))
        if "additional_conditions" not in rule_columns:
            additional_conditions_type = (
                "JSON NOT NULL DEFAULT '[]'::json"
                if connection.dialect.name == "postgresql"
                else "JSON NOT NULL DEFAULT '[]'"
            )
            connection.execute(
                text(
                    "ALTER TABLE rules "
                    f"ADD COLUMN additional_conditions {additional_conditions_type}"
                )
            )
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rules_user_id ON rules (user_id)"))

    if "article_matches" in table_names:
        match_columns = {column["name"] for column in inspector.get_columns("article_matches")}
        if "user_id" not in match_columns:
            connection.execute(text("ALTER TABLE article_matches ADD COLUMN user_id INTEGER"))
        if "push_notified_at" not in match_columns:
            timestamp_type = (
                "TIMESTAMP WITHOUT TIME ZONE"
                if connection.dialect.name == "postgresql"
                else "DATETIME"
            )
            connection.execute(
                text(
                    "ALTER TABLE article_matches "
                    f"ADD COLUMN push_notified_at {timestamp_type}"
                )
            )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_article_matches_user_id ON article_matches (user_id)")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_article_matches_push_notified_at "
                "ON article_matches (push_notified_at)"
            )
        )


def _ensure_scheduler_columns(connection: Connection) -> None:
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    if "app_settings" in table_names:
        setting_columns = {
            column["name"] for column in inspector.get_columns("app_settings")
        }
        if "interval_seconds" not in setting_columns:
            connection.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN interval_seconds INTEGER NOT NULL DEFAULT 30"
                )
            )
            connection.execute(
                text(
                    "UPDATE app_settings "
                    "SET interval_seconds = 30, pages_per_board = 1 "
                    "WHERE id = 1"
                )
            )

    if "worker_state" in table_names:
        worker_columns = {
            column["name"] for column in inspector.get_columns("worker_state")
        }
        if "interval_seconds" not in worker_columns:
            connection.execute(
                text(
                    "ALTER TABLE worker_state "
                    "ADD COLUMN interval_seconds INTEGER NOT NULL DEFAULT 30"
                )
            )


def _initialize_schema(connection: Connection) -> None:
    Base.metadata.create_all(bind=connection)
    _ensure_account_columns(connection)
    _ensure_scheduler_columns(connection)


def initialize_database() -> None:
    if engine.dialect.name != "postgresql":
        with engine.begin() as connection:
            _initialize_schema(connection)
        return

    advisory_lock_key = 781_046_213
    with engine.connect() as connection:
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_key)"),
            {"lock_key": advisory_lock_key},
        )
        try:
            _initialize_schema(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": advisory_lock_key},
            )
            connection.commit()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
