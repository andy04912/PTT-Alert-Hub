from app.models import Rule, RuleMatchType
from app.services.ptt_crawler import PttArticle


def article_matches_rule(article: PttArticle, rule: Rule) -> bool:
    if rule.match_type == RuleMatchType.AUTHOR:
        if rule.case_sensitive:
            return article.author == rule.pattern
        return article.author.casefold() == rule.pattern.casefold()

    if rule.case_sensitive:
        return rule.pattern in article.title
    return rule.pattern.casefold() in article.title.casefold()
