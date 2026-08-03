from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BoardCrawlSnapshot, CrawlRun, CrawlRunStatus
from app.services.crawl_service import CrawlService
from app.services.ptt_crawler import PttArticle


def create_test_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def make_article(key: str, title: str) -> PttArticle:
    return PttArticle(
        article_key=key,
        board="Tech_Job",
        title=title,
        author="tester",
        url=f"https://www.ptt.cc{key}",
        ptt_date="8/03",
        published_at=datetime(2026, 8, 3, 5, 0, 0),
    )


def test_snapshot_is_replaced_instead_of_appended() -> None:
    engine = create_test_engine()

    with Session(engine) as db:
        first_run = CrawlRun(status=CrawlRunStatus.SUCCESS)
        second_run = CrawlRun(status=CrawlRunStatus.SUCCESS)
        db.add_all([first_run, second_run])
        db.commit()

        CrawlService._replace_board_snapshot(
            db,
            first_run.id,
            "Tech_Job",
            [make_article("/bbs/Tech_Job/M.1.html", "First")],
        )
        db.commit()

        CrawlService._replace_board_snapshot(
            db,
            second_run.id,
            "Tech_Job",
            [
                make_article("/bbs/Tech_Job/M.2.html", "Second"),
                make_article("/bbs/Tech_Job/M.3.html", "Third"),
            ],
        )
        db.commit()

        snapshots = list(db.scalars(select(BoardCrawlSnapshot)).all())
        assert len(snapshots) == 1
        assert snapshots[0].run_id == second_run.id
        assert snapshots[0].articles_count == 2
        assert [article["title"] for article in snapshots[0].articles] == ["Second", "Third"]


def test_prune_removes_snapshots_for_inactive_boards() -> None:
    engine = create_test_engine()

    with Session(engine) as db:
        run = CrawlRun(status=CrawlRunStatus.SUCCESS)
        db.add(run)
        db.commit()
        db.add_all(
            [
                BoardCrawlSnapshot(board="Tech_Job", run_id=run.id, articles=[]),
                BoardCrawlSnapshot(board="MacShop", run_id=run.id, articles=[]),
            ]
        )
        db.commit()

        CrawlService._prune_board_snapshots(db, {"Tech_Job"})
        db.commit()

        boards = list(
            db.scalars(
                select(BoardCrawlSnapshot.board).order_by(BoardCrawlSnapshot.board)
            ).all()
        )
        assert boards == ["Tech_Job"]
