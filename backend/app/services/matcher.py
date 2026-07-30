from app.models import Rule, RuleMatchType
from app.services.ptt_crawler import PttArticle


def _contains(value: str, pattern: str, *, case_sensitive: bool) -> bool:
    if case_sensitive:
        return pattern in value
    return pattern.casefold() in value.casefold()


def article_matches_rule(article: PttArticle, rule: Rule) -> bool:
    excluded_keywords = getattr(rule, "excluded_keywords", None) or []
    if any(
        _contains(article.title, keyword, case_sensitive=rule.case_sensitive)
        for keyword in excluded_keywords
    ):
        return False

    if rule.match_type == RuleMatchType.AUTHOR:
        if rule.case_sensitive:
            return article.author == rule.pattern
        return article.author.casefold() == rule.pattern.casefold()

    return _contains(article.title, rule.pattern, case_sensitive=rule.case_sensitive)
