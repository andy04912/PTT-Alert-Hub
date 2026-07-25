from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.database import SessionLocal
from app.models import WorkerState, utc_now
from app.services.app_settings import get_or_create_app_settings
from app.services.crawl_service import crawl_service
from app.services.distributed_lock import distributed_lock_service

CRAWL_JOB_ID = "ptt-crawl-job"
WORKER_SYNC_JOB_ID = "worker-sync-job"
WORKER_LEASE_NAME = "crawler-worker-leader"


class SchedulerService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.worker_id = uuid4().hex
        self.scheduler = BackgroundScheduler(timezone=self.settings.timezone)
        self._leader = False
        self._current_interval_minutes: int | None = None

    @property
    def running(self) -> bool:
        return self.scheduler.running

    def start(self) -> None:
        if self.scheduler.running:
            return

        self.scheduler.add_job(
            self._sync_worker,
            trigger=IntervalTrigger(seconds=self.settings.worker_sync_seconds),
            id=WORKER_SYNC_JOB_ID,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            next_run_time=datetime.now(UTC),
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        if self._leader:
            distributed_lock_service.release(WORKER_LEASE_NAME, self.worker_id)
        self._leader = False
        self._mark_worker_stopped()

    def _sync_worker(self) -> None:
        is_leader = distributed_lock_service.try_acquire(
            name=WORKER_LEASE_NAME,
            owner=self.worker_id,
            ttl_seconds=self.settings.worker_lease_ttl_seconds,
        )
        self._leader = is_leader

        if not is_leader:
            self._remove_crawl_job()
            return

        interval_minutes = self._get_interval_minutes()
        self._ensure_crawl_job(interval_minutes)
        self._write_worker_state(interval_minutes)

    def _ensure_crawl_job(self, interval_minutes: int) -> None:
        job = self.scheduler.get_job(CRAWL_JOB_ID)
        if job is None:
            self.scheduler.add_job(
                crawl_service.run,
                trigger=IntervalTrigger(minutes=interval_minutes),
                kwargs={"trigger": "scheduler"},
                id=CRAWL_JOB_ID,
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=120,
            )
            self._current_interval_minutes = interval_minutes
            return

        if self._current_interval_minutes == interval_minutes:
            return

        self.scheduler.reschedule_job(
            CRAWL_JOB_ID,
            trigger=IntervalTrigger(minutes=interval_minutes),
        )
        self._current_interval_minutes = interval_minutes

    def _remove_crawl_job(self) -> None:
        if self.scheduler.get_job(CRAWL_JOB_ID) is not None:
            self.scheduler.remove_job(CRAWL_JOB_ID)
        self._current_interval_minutes = None

    def _write_worker_state(self, interval_minutes: int) -> None:
        crawl_job = self.scheduler.get_job(CRAWL_JOB_ID)
        next_run_at = self._to_naive_utc(crawl_job.next_run_time) if crawl_job else None
        now = utc_now()

        db = SessionLocal()
        try:
            worker_state = db.get(WorkerState, 1)
            if worker_state is None:
                worker_state = WorkerState(
                    id=1,
                    worker_id=self.worker_id,
                    active=True,
                    started_at=now,
                    heartbeat_at=now,
                    next_run_at=next_run_at,
                    interval_minutes=interval_minutes,
                )
            else:
                if worker_state.worker_id != self.worker_id:
                    worker_state.started_at = now
                worker_state.worker_id = self.worker_id
                worker_state.active = True
                worker_state.heartbeat_at = now
                worker_state.next_run_at = next_run_at
                worker_state.interval_minutes = interval_minutes

            db.add(worker_state)
            db.commit()
        finally:
            db.close()

    def _mark_worker_stopped(self) -> None:
        db = SessionLocal()
        try:
            worker_state = db.get(WorkerState, 1)
            if worker_state is None or worker_state.worker_id != self.worker_id:
                return
            worker_state.active = False
            worker_state.heartbeat_at = utc_now()
            worker_state.next_run_at = None
            db.add(worker_state)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _get_interval_minutes() -> int:
        db = SessionLocal()
        try:
            return get_or_create_app_settings(db).interval_minutes
        finally:
            db.close()

    @staticmethod
    def _to_naive_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)


scheduler_service = SchedulerService()
