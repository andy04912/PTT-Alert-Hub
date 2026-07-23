from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core.boards import normalize_board_name
from app.dependencies import AdminUser, DbSession
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


@router.get("", response_model=list[RuleRead])
def list_rules(db: DbSession, _admin: AdminUser) -> list[Rule]:
    return list(db.scalars(select(Rule).order_by(Rule.board, Rule.id)).all())


@router.post("", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(payload: RuleCreate, db: DbSession, _admin: AdminUser) -> Rule:
    valid, message = crawler.validate_board(payload.board)
    if not valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    rule = Rule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=RuleRead)
def update_rule(rule_id: int, payload: RuleUpdate, db: DbSession, _admin: AdminUser) -> Rule:
    rule = db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到規則")

    if rule.board != payload.board:
        valid, message = crawler.validate_board(payload.board)
        if not valid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    for field, value in payload.model_dump().items():
        setattr(rule, field, value)

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: DbSession, _admin: AdminUser) -> Response:
    rule = db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到規則")

    db.delete(rule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/validate/{board}", response_model=BoardValidationResponse)
def validate_board(board: str, _admin: AdminUser) -> BoardValidationResponse:
    normalized_board = normalize_board_name(board)
    valid, message = crawler.validate_board(normalized_board)
    return BoardValidationResponse(board=normalized_board, valid=valid, message=message)
