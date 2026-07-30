from app.models import Rule, RuleConditionOperator, RuleMatchType
from app.services.matcher import article_matches_rule
from app.services.ptt_crawler import PttArticle


def make_article(title: str, author: str) -> PttArticle:
    return PttArticle(
        article_key="/bbs/Tech_Job/M.123.A.001.html",
        board="Tech_Job",
        title=title,
        author=author,
        url="https://www.ptt.cc/bbs/Tech_Job/M.123.A.001.html",
        ptt_date="7/23",
        published_at=None,
    )


def test_title_keyword_match() -> None:
    rule = Rule(
        name="徵才",
        board="Tech_Job",
        match_type=RuleMatchType.TITLE_KEYWORD,
        pattern="徵才",
        enabled=True,
        case_sensitive=False,
    )
    assert article_matches_rule(make_article("[徵才] React 工程師", "company"), rule)


def test_author_exact_match_is_case_insensitive_by_default() -> None:
    rule = Rule(
        name="指定作者",
        board="Taichung",
        match_type=RuleMatchType.AUTHOR,
        pattern="Andy123",
        enabled=True,
        case_sensitive=False,
    )
    assert article_matches_rule(make_article("[閒聊] 台中天氣", "andy123"), rule)


def test_title_match_requires_all_include_conditions() -> None:
    rule = Rule(
        name="Mac mini M3 販賣",
        board="MacShop",
        match_type=RuleMatchType.TITLE_KEYWORD,
        pattern="Mac mini",
        additional_conditions=[
            {
                "operator": RuleConditionOperator.TITLE_CONTAINS,
                "pattern": "M3",
            }
        ],
        enabled=True,
        case_sensitive=False,
    )

    assert article_matches_rule(make_article("[販售] M3 Mac mini 16GB", "seller"), rule)
    assert not article_matches_rule(make_article("[販售] M4 Mac mini 16GB", "seller"), rule)


def test_title_match_combines_include_and_exclude_conditions() -> None:
    rule = Rule(
        name="Mac mini M3 販賣",
        board="MacShop",
        match_type=RuleMatchType.TITLE_KEYWORD,
        pattern="Mac mini",
        additional_conditions=[
            {
                "operator": RuleConditionOperator.TITLE_CONTAINS,
                "pattern": "M3",
            },
            {
                "operator": RuleConditionOperator.TITLE_NOT_CONTAINS,
                "pattern": "徵求",
            },
        ],
        enabled=True,
        case_sensitive=False,
    )

    assert article_matches_rule(make_article("[販售] M3 Mac mini", "seller"), rule)
    assert not article_matches_rule(make_article("[徵求] M3 Mac mini", "buyer"), rule)
    assert not article_matches_rule(make_article("[販售] M4 Mac mini", "seller"), rule)


def test_author_exact_match_can_use_additional_title_conditions() -> None:
    rule = Rule(
        name="指定賣家的 Mac mini",
        board="MacShop",
        match_type=RuleMatchType.AUTHOR,
        pattern="Brady",
        additional_conditions=[
            {
                "operator": RuleConditionOperator.TITLE_CONTAINS,
                "pattern": "Mac mini",
            },
            {
                "operator": RuleConditionOperator.TITLE_NOT_CONTAINS,
                "pattern": "已售出",
            },
        ],
        enabled=True,
        case_sensitive=False,
    )

    assert article_matches_rule(make_article("[販售] Mac mini", "brady"), rule)
    assert not article_matches_rule(make_article("[販售] Mac mini 已售出", "BRADY"), rule)
    assert not article_matches_rule(make_article("[販售] MacBook Air", "brady"), rule)
