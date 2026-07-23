import sqlite3
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
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


def initialize_database() -> None:
    if engine.dialect.name != "postgresql":
        Base.metadata.create_all(bind=engine)
        return

    advisory_lock_key = 781_046_213
    with engine.connect() as connection:
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_key)"),
            {"lock_key": advisory_lock_key},
        )
        try:
            Base.metadata.create_all(bind=connection)
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
