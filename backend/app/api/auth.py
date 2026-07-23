from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.core.security import authenticate_admin, create_access_token
from app.dependencies import AdminUser
from app.schemas import CurrentUser, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    if not authenticate_admin(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
        )
    return TokenResponse(access_token=create_access_token(payload.username))


@router.get("/me", response_model=CurrentUser)
def get_me(admin: AdminUser) -> CurrentUser:
    return CurrentUser(username=admin)
