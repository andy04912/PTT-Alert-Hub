from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.dependencies import CurrentUser, DbSession
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services.account_service import authenticate_user, create_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _build_token_response(user) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    try:
        user = create_user(
            db,
            email=str(payload.email),
            display_name=payload.display_name,
            password=payload.password,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    return _build_token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email 或密碼錯誤",
        )
    return _build_token_response(user)


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
