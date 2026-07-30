from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core.boards import normalize_board_name
from app.dependencies import CurrentUser, DbSession
from app.models import Rule
from app.schemas import (
    BoardValidationResponse,
    RuleCreate,
    RuleRead,
    RuleUpdate,
)
from app.services.ptt_crawler import PttCrawler

router = APIRouter(prefix="/api/rules", tags=["rules"])
crawler = PttCrawler()


def _get_owned_rule(db: DbSession, user_id: int, rule_id: int) -> Rule:
    rule = db.scalar(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.user_id == user_id,
        )
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到規則")
    return rule


def _rule_payload_data(payload: RuleCreate | RuleUpdate) -> dict:
    data = payload.model_dump()
    data["additional_conditions"] = [
        condition.model_dump(mode="json")
        for condition in payload.additional_conditions
    ]
    return data


@router.get("", response_model=list[RuleRead])
def list_rules(db: DbSession, current_user: CurrentUser) -> list[Rule]:
    return list(
        db.scalars(
            select(Rule)
            .where(Rule.user_id == current_user.id)
            .order_by(Rule.board, Rule.id)
        ).all()
    )


@router.post("", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(payload: RuleCreate, db: DbSession, current_user: CurrentUser) -> Rule:
    valid, message = crawler.validate_board(payload.board)
    if not valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    rule = Rule(user_id=current_user.id, **_rule_payload_data(payload))
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=RuleRead)
def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Rule:
    rule = _get_owned_rule(db, current_user.id, rule_id)

    if rule.board != payload.board:
        valid, message = crawler.validate_board(payload.board)
        if not valid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    for field, value in _rule_payload_data(payload).items():
        setattr(rule, field, value)

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    rule = _get_owned_rule(db, current_user.id, rule_id)
    db.delete(rule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/validate/{board}", response_model=BoardValidationResponse)
def validate_board(board: str, _current_user: CurrentUser) -> BoardValidationResponse:
    normalized_board = normalize_board_name(board)
    valid, message = crawler.validate_board(normalized_board)
    return BoardValidationResponse(board=normalized_board, valid=valid, message=message)
