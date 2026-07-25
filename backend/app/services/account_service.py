from pwdlib import PasswordHash
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Rule, User

settings = get_settings()
password_hash = PasswordHash.recommended()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def ensure_bootstrap_admin(db: Session) -> User:
    email = settings.normalized_bootstrap_admin_email
    admin = db.scalar(select(User).where(User.email == email))

    if admin is None:
        admin = User(
            email=email,
            display_name=settings.bootstrap_admin_display_name.strip() or "系統管理員",
            password_hash=hash_password(settings.bootstrap_admin_password),
            is_active=True,
            is_admin=True,
        )
        db.add(admin)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            admin = db.scalar(select(User).where(User.email == email))
            if admin is None:
                raise
        else:
            db.refresh(admin)
    elif not admin.is_admin:
        admin.is_admin = True
        db.add(admin)
        db.commit()
        db.refresh(admin)

    db.execute(
        update(Rule)
        .where(Rule.user_id.is_(None))
        .values(user_id=admin.id)
    )
    db.execute(
        text(
            "UPDATE article_matches "
            "SET user_id = ("
            "SELECT rules.user_id FROM rules WHERE rules.id = article_matches.rule_id"
            ") "
            "WHERE user_id IS NULL"
        )
    )
    db.commit()
    return admin


def create_user(
    db: Session,
    *,
    email: str,
    display_name: str,
    password: str,
) -> User:
    user = User(
        email=normalize_email(email),
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError("這個 Email 已經註冊") from error
    db.refresh(user)
    return user
