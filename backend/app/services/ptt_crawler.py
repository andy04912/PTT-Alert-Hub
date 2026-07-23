from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.core.boards import normalize_board_name
from app.core.config import get_settings

ARTICLE_TIMESTAMP_PATTERN = re.compile(r"/M\.(\d+)\.")


class PttCrawlerError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PttArticle:
    article_key: str
    board: str
    title: str
    author: str
    url: str
    ptt_date: str
    published_at: datetime | None


class PttCrawler:
    _request_lock = threading.Lock()
    _last_request_at = 0.0

    def __init__(self) -> None:
        self.settings = get_settings()

    def crawl_board(self, board: str, pages: int) -> list[PttArticle]:
        board = normalize_board_name(board)
        if not board:
            raise PttCrawlerError("看板名稱不可為空")

        current_url = f"{self.settings.ptt_base_url}/bbs/{board}/index.html"
        articles: dict[str, PttArticle] = {}

        with self._create_client() as client:
            for page_index in range(pages):
                response = self._get(client, current_url)
                page_articles, previous_page_url = self.parse_index_page(
                    response.text,
                    board=board,
                    base_url=self.settings.ptt_base_url,
                )

                if page_index == 0 and not page_articles and not self._looks_like_board(response.text, board):
                    raise PttCrawlerError(f"找不到 PTT 看板：{board}")

                for article in page_articles:
                    articles.setdefault(article.article_key, article)

                if not previous_page_url:
                    break

                current_url = previous_page_url

        return list(articles.values())

    def validate_board(self, board: str) -> tuple[bool, str]:
        try:
            articles = self.crawl_board(board, pages=1)
        except PttCrawlerError as error:
            return False, str(error)
        return True, f"看板可正常讀取，目前頁面取得 {len(articles)} 篇文章"

    def _create_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; PttAlertHub/1.0; "
                    "+https://github.com/)"
                ),
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            },
            cookies={"over18": "1"},
            follow_redirects=True,
            timeout=self.settings.ptt_timeout_seconds,
            transport=httpx.HTTPTransport(retries=2),
        )

    @staticmethod
    def _looks_like_board(html: str, board: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        board_label = soup.select_one(".board-name")
        board_name = board_label.get_text(strip=True) if board_label else ""
        return board.lower() in title.lower() or board.lower() == board_name.lower()

    def _get(self, client: httpx.Client, url: str) -> httpx.Response:
        retryable_statuses = {429, 500, 502, 503, 504}

        for attempt in range(3):
            with self._request_lock:
                elapsed = time.monotonic() - self.__class__._last_request_at
                wait_seconds = self.settings.ptt_request_delay_seconds - elapsed
                if wait_seconds > 0:
                    time.sleep(wait_seconds)

                try:
                    response = client.get(url)
                except httpx.HTTPError as error:
                    self.__class__._last_request_at = time.monotonic()
                    if attempt == 2:
                        raise PttCrawlerError(f"讀取 PTT 失敗：{error}") from error
                    time.sleep(2 ** attempt)
                    continue

                self.__class__._last_request_at = time.monotonic()

            if response.status_code not in retryable_statuses:
                try:
                    response.raise_for_status()
                except httpx.HTTPError as error:
                    raise PttCrawlerError(f"讀取 PTT 失敗：{error}") from error
                return response

            if attempt == 2:
                raise PttCrawlerError(
                    f"PTT 暫時拒絕或無法處理請求（HTTP {response.status_code}）"
                )

            retry_after = response.headers.get("Retry-After")
            try:
                backoff_seconds = float(retry_after) if retry_after else float(2 ** attempt)
            except ValueError:
                backoff_seconds = float(2 ** attempt)
            time.sleep(max(backoff_seconds, self.settings.ptt_request_delay_seconds))

        raise PttCrawlerError("讀取 PTT 失敗")

    @staticmethod
    def parse_index_page(
        html: str,
        *,
        board: str,
        base_url: str,
    ) -> tuple[list[PttArticle], str | None]:
        soup = BeautifulSoup(html, "html.parser")
        articles: list[PttArticle] = []

        for entry in soup.select("div.r-ent"):
            title_element = entry.select_one("div.title a")
            if title_element is None:
                continue

            href = title_element.get("href")
            if not isinstance(href, str) or not href:
                continue

            title = title_element.get_text(" ", strip=True)
            author_element = entry.select_one("div.author")
            date_element = entry.select_one("div.date")
            author = author_element.get_text(strip=True) if author_element else ""
            ptt_date = date_element.get_text(strip=True) if date_element else ""
            url = urljoin(base_url, href)
            published_at = PttCrawler._extract_published_at(href)

            articles.append(
                PttArticle(
                    article_key=href,
                    board=board,
                    title=title,
                    author=author,
                    url=url,
                    ptt_date=ptt_date,
                    published_at=published_at,
                )
            )

        previous_page_url: str | None = None
        for link in soup.select("a.btn.wide"):
            if "上頁" not in link.get_text(" ", strip=True):
                continue
            href = link.get("href")
            if isinstance(href, str) and href:
                previous_page_url = urljoin(base_url, href)
                break

        return articles, previous_page_url

    @staticmethod
    def _extract_published_at(href: str) -> datetime | None:
        match = ARTICLE_TIMESTAMP_PATTERN.search(href)
        if not match:
            return None
        try:
            return datetime.fromtimestamp(int(match.group(1)), tz=timezone.utc).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None
