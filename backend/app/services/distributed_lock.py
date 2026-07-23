from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from typing import Iterator
from uuid import uuid4

from sqlalchemy import delete, insert, or_, update
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import RuntimeLock, utc_now


class DistributedLockService:
    def try_acquire(self, name: str, owner: str, ttl_seconds: int) -> bool:
        now = utc_now()
        expires_at = now + timedelta(seconds=ttl_seconds)
        db = SessionLocal()
        try:
            try:
                db.execute(
                    insert(RuntimeLock).values(
                        name=name,
                        owner=owner,
                        acquired_at=now,
                        expires_at=expires_at,
                    )
                )
                db.commit()
                return True
            except IntegrityError:
                db.rollback()

            result = db.execute(
                update(RuntimeLock)
                .where(
                    RuntimeLock.name == name,
                    or_(RuntimeLock.owner == owner, RuntimeLock.expires_at < now),
                )
                .values(
                    owner=owner,
                    acquired_at=now,
                    expires_at=expires_at,
                )
            )
            db.commit()
            return result.rowcount == 1
        finally:
            db.close()

    def release(self, name: str, owner: str) -> None:
        db = SessionLocal()
        try:
            db.execute(
                delete(RuntimeLock).where(
                    RuntimeLock.name == name,
                    RuntimeLock.owner == owner,
                )
            )
            db.commit()
        finally:
            db.close()

    @contextmanager
    def acquire(self, name: str, ttl_seconds: int) -> Iterator[bool]:
        owner = uuid4().hex
        acquired = self.try_acquire(name=name, owner=owner, ttl_seconds=ttl_seconds)
        try:
            yield acquired
        finally:
            if acquired:
                self.release(name=name, owner=owner)


distributed_lock_service = DistributedLockService()
