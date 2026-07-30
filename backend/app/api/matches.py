from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models import ArticleMatch, Rule, SeenArticle

router = APIRouter(prefix="/api/matches", tags=["matches"])


class ArticleMatchRead(BaseModel):
    id: int
    rule_id: int
    rule_name: str
    board: str
    title: str
    author: str
    url: str
    published_at: datetime | None
    matched_at: datetime
    notified_at: datetime | None
    push_notified_at: datetime | None


@router.get("", response_model=list[ArticleMatchRead])
def list_matches(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ArticleMatchRead]:
    rows = db.execute(
        select(ArticleMatch, Rule, SeenArticle)
        .join(Rule, Rule.id == ArticleMatch.rule_id)
        .join(SeenArticle, SeenArticle.id == ArticleMatch.article_id)
        .where(ArticleMatch.user_id == current_user.id)
        .order_by(ArticleMatch.matched_at.desc(), ArticleMatch.id.desc())
        .limit(limit)
    ).all()

    return [
        ArticleMatchRead(
            id=article_match.id,
            rule_id=rule.id,
            rule_name=rule.name,
            board=article.board,
            title=article.title,
            author=article.author,
            url=article.url,
            published_at=article.published_at,
            matched_at=article_match.matched_at,
            notified_at=article_match.notified_at,
            push_notified_at=article_match.push_notified_at,
        )
        for article_match, rule, article in rows
    ]
