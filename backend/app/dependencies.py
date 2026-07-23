from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import bearer_scheme, get_current_admin
from app.database import get_db

DbSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]


def require_admin(credentials: BearerCredentials) -> str:
    return get_current_admin(credentials)


AdminUser = Annotated[str, Depends(require_admin)]
