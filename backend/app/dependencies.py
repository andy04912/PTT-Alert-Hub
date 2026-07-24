from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import bearer_scheme, decode_access_token
from app.database import get_db
from app.models import User

DbSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]


def require_user(db: DbSession, credentials: BearerCredentials) -> User:
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號不存在或已停用",
        )
    return user


CurrentUser = Annotated[User, Depends(require_user)]


def require_admin(current_user: CurrentUser) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此功能僅限系統管理員使用",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
