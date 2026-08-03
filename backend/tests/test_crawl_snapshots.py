from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.crawl import list_latest_results
from app.database import Base
from app.models import (
    BoardCrawlSnapshot,
    CrawlRun,
    CrawlRunStatus,
    Rule,
    RuleMatchType,
)
from app.services.account_service import create_user
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


def test_latest_results_only_include_current_users_enabled_boards() -> None:
    engine = create_test_engine()

    with Session(engine) as db:
        user_a = create_user(
            db,
            email="a@example.com",
            display_name="User A",
            password="strong-password-123",
        )
        user_b = create_user(
            db,
            email="b@example.com",
            display_name="User B",
            password="strong-password-123",
        )
        run = CrawlRun(status=CrawlRunStatus.SUCCESS)
        db.add(run)
        db.commit()

        db.add_all(
            [
                Rule(
                    user_id=user_a.id,
                    name="A active",
                    board="Tech_Job",
                    match_type=RuleMatchType.TITLE_KEYWORD,
                    pattern="Python",
                    enabled=True,
                ),
                Rule(
                    user_id=user_a.id,
                    name="A disabled",
                    board="MacShop",
                    match_type=RuleMatchType.TITLE_KEYWORD,
                    pattern="Mac mini",
                    enabled=False,
                ),
                Rule(
                    user_id=user_b.id,
                    name="B active",
                    board="Stock",
                    match_type=RuleMatchType.TITLE_KEYWORD,
                    pattern="台積電",
                    enabled=True,
                ),
                BoardCrawlSnapshot(board="Tech_Job", run_id=run.id, articles=[]),
                BoardCrawlSnapshot(board="MacShop", run_id=run.id, articles=[]),
                BoardCrawlSnapshot(board="Stock", run_id=run.id, articles=[]),
            ]
        )
        db.commit()

        user_a_results = list_latest_results(db, user_a)
        user_b_results = list_latest_results(db, user_b)

        assert [snapshot.board for snapshot in user_a_results] == ["Tech_Job"]
        assert [snapshot.board for snapshot in user_b_results] == ["Stock"]
