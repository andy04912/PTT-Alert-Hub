from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser
from app.schemas import BoardCategoryRead, BoardOptionRead
from app.services.board_directory import (
    BoardDirectoryError,
    board_directory_service,
)

router = APIRouter(prefix="/api/boards", tags=["boards"])


def _option_to_response(option) -> BoardOptionRead:
    return BoardOptionRead(
        board=option.board,
        category=option.category,
        title=option.title,
        popularity=option.popularity,
        source=option.source,
    )


@router.get("/popular", response_model=list[BoardOptionRead])
def list_popular_boards(
    _current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[BoardOptionRead]:
    try:
        return [
            _option_to_response(option)
            for option in board_directory_service.get_popular_boards(limit=limit)
        ]
    except BoardDirectoryError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error


@router.get("/search", response_model=list[BoardOptionRead])
def search_boards(
    _current_user: CurrentUser,
    q: str = Query(default="", max_length=80),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[BoardOptionRead]:
    try:
        return [
            _option_to_response(option)
            for option in board_directory_service.search_boards(q, limit=limit)
        ]
    except BoardDirectoryError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error


@router.get("/categories/{category_id}", response_model=BoardCategoryRead)
def browse_category(category_id: int, _current_user: CurrentUser) -> BoardCategoryRead:
    try:
        category = board_directory_service.get_category(category_id)
    except BoardDirectoryError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return BoardCategoryRead(
        category_id=category.category_id,
        title=category.title,
        entries=[
            {
                "kind": entry.kind,
                "name": entry.name,
                "description": entry.description,
                "board": entry.board,
                "category_id": entry.category_id,
                "category": entry.category,
                "popularity": entry.popularity,
            }
            for entry in category.entries
        ],
    )
