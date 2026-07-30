from app.models import Rule, RuleConditionOperator, RuleMatchType
from app.services.ptt_crawler import PttArticle


def _contains(value: str, pattern: str, *, case_sensitive: bool) -> bool:
    if case_sensitive:
        return pattern in value
    return pattern.casefold() in value.casefold()


def _primary_condition_matches(article: PttArticle, rule: Rule) -> bool:
    if rule.match_type == RuleMatchType.AUTHOR:
        if rule.case_sensitive:
            return article.author == rule.pattern
        return article.author.casefold() == rule.pattern.casefold()

    return _contains(article.title, rule.pattern, case_sensitive=rule.case_sensitive)


def article_matches_rule(article: PttArticle, rule: Rule) -> bool:
    if not _primary_condition_matches(article, rule):
        return False

    additional_conditions = getattr(rule, "additional_conditions", None) or []
    for condition in additional_conditions:
        operator = condition.get("operator")
        pattern = condition.get("pattern", "")
        contains_pattern = _contains(
            article.title,
            pattern,
            case_sensitive=rule.case_sensitive,
        )

        if operator == RuleConditionOperator.TITLE_CONTAINS:
            if not contains_pattern:
                return False
            continue

        if operator == RuleConditionOperator.TITLE_NOT_CONTAINS:
            if contains_pattern:
                return False
            continue

        return False

    return True
