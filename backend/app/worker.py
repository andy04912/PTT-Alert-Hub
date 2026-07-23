from __future__ import annotations

import signal
import threading

from app.database import SessionLocal, initialize_database
from app.services.app_settings import get_or_create_app_settings
from app.services.scheduler_service import scheduler_service


def initialize_worker() -> None:
    initialize_database()
    db = SessionLocal()
    try:
        get_or_create_app_settings(db)
    finally:
        db.close()


def main() -> None:
    initialize_worker()
    stop_event = threading.Event()

    def request_shutdown(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    scheduler_service.start()
    try:
        stop_event.wait()
    finally:
        scheduler_service.shutdown()


if __name__ == "__main__":
    main()
