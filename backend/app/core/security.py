import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=True)


def authenticate_admin(username: str, password: str) -> bool:
    username_matches = hmac.compare_digest(username, settings.admin_username)
    password_matches = hmac.compare_digest(password, settings.admin_password)
    return username_matches and password_matches


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登入憑證無效或已過期",
        ) from error

    subject = payload.get("sub")
    if not isinstance(subject, str) or subject != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登入憑證無效",
        )
    return subject


def get_current_admin(credentials: HTTPAuthorizationCredentials) -> str:
    return decode_access_token(credentials.credentials)
