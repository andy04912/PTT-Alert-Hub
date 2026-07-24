from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, decode_access_token
from app.database import Base
from app.models import Rule, RuleMatchType
from app.services.account_service import authenticate_user, create_user


def create_test_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def test_user_registration_hashes_password_and_authenticates() -> None:
    engine = create_test_engine()

    with Session(engine) as db:
        user = create_user(
            db,
            email="Brady@example.com",
            display_name="Brady",
            password="strong-password-123",
        )

        assert user.email == "brady@example.com"
        assert user.password_hash != "strong-password-123"
        assert authenticate_user(db, "BRADY@example.com", "strong-password-123") == user
        assert authenticate_user(db, "brady@example.com", "wrong-password") is None


def test_jwt_subject_is_database_user_id() -> None:
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_rules_can_be_scoped_to_each_user() -> None:
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
        db.add_all(
            [
                Rule(
                    user_id=user_a.id,
                    name="A rule",
                    board="Tech_Job",
                    match_type=RuleMatchType.TITLE_KEYWORD,
                    pattern="徵才",
                ),
                Rule(
                    user_id=user_b.id,
                    name="B rule",
                    board="TaichungBun",
                    match_type=RuleMatchType.AUTHOR,
                    pattern="andy123",
                ),
            ]
        )
        db.commit()

        user_a_rules = list(
            db.scalars(select(Rule).where(Rule.user_id == user_a.id)).all()
        )
        user_b_rules = list(
            db.scalars(select(Rule).where(Rule.user_id == user_b.id)).all()
        )

        assert [rule.name for rule in user_a_rules] == ["A rule"]
        assert [rule.name for rule in user_b_rules] == ["B rule"]
