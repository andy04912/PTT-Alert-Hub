from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.models import Rule
from app.services.ptt_crawler import PttArticle

TELEGRAM_MESSAGE_LIMIT = 4096
SAFE_MESSAGE_LIMIT = 3900


class NotificationError(RuntimeError):
    pass


@dataclass(slots=True)
class MatchedArticle:
    article: PttArticle
    rules: list[Rule]
    match_ids: list[int]


class TelegramNotifier:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return self.settings.telegram_configured

    def send(self, message: str) -> None:
        if not self.configured:
            raise NotificationError("尚未設定 Telegram Bot Token 或 Chat ID")

        endpoint = (
            f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        )
        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "text": message[:TELEGRAM_MESSAGE_LIMIT],
            "disable_web_page_preview": True,
        }

        try:
            response = httpx.post(endpoint, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise NotificationError(f"Telegram 通知失敗：{error}") from error

        if not result.get("ok"):
            description = result.get("description", "未知錯誤")
            raise NotificationError(f"Telegram 通知失敗：{description}")

    def send_test(self) -> None:
        self.send("✅ PTT Alert Hub 測試通知成功。")


def build_notification_message(matches: list[MatchedArticle], pending_count: int = 0) -> str:
    grouped_by_board: dict[str, list[MatchedArticle]] = defaultdict(list)
    for match in matches:
        grouped_by_board[match.article.board].append(match)

    total_rules = len({rule.id for match in matches for rule in match.rules})
    lines = [
        "🔔 PTT 新文章通知",
        f"本次共 {len(matches)} 篇文章符合 {total_rules} 條規則。",
        "",
    ]

    for board, board_matches in grouped_by_board.items():
        lines.append(f"【{board}】")
        for match in board_matches:
            rule_names = "、".join(rule.name for rule in match.rules)
            if len(rule_names) > 320:
                rule_names = f"{rule_names[:317]}…"
            title = match.article.title
            if len(title) > 320:
                title = f"{title[:317]}…"
            lines.extend(
                [
                    f"• {title}",
                    f"  作者：{match.article.author or '未知'}",
                    f"  命中：{rule_names}",
                    f"  {match.article.url}",
                    "",
                ]
            )

    if pending_count > len(matches):
        lines.append(f"尚有 {pending_count - len(matches)} 篇待下次通知。")

    return "\n".join(lines).strip()
