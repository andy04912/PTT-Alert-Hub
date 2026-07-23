from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from typing import Literal
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup

from app.core.boards import BOARD_SEARCH_KEYWORDS, normalize_board_name
from app.core.config import get_settings
from app.services.ptt_crawler import PttCrawler

BOARD_LINK_PATTERN = re.compile(r"^/bbs/([^/]+)/index\.html$")
CATEGORY_LINK_PATTERN = re.compile(r"^/cls/(\d+)/?$")

BoardSource = Literal["popular", "category", "exact"]
DirectoryEntryKind = Literal["board", "category"]


class BoardDirectoryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BoardOptionData:
    board: str
    category: str
    title: str
    popularity: int | None
    source: BoardSource


@dataclass(frozen=True, slots=True)
class BoardDirectoryEntryData:
    kind: DirectoryEntryKind
    name: str
    description: str
    board: str | None = None
    category_id: int | None = None
    category: str = ""
    popularity: int | None = None


@dataclass(frozen=True, slots=True)
class BoardCategoryData:
    category_id: int
    title: str
    entries: list[BoardDirectoryEntryData]


class BoardDirectoryService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.crawler = PttCrawler()
        self._lock = threading.RLock()
        self._popular_cache: tuple[float, list[BoardOptionData]] | None = None
        self._category_cache: dict[int, tuple[float, BoardCategoryData]] = {}
        self._known_boards: dict[str, BoardOptionData] = {}

    def get_popular_boards(self, limit: int = 100) -> list[BoardOptionData]:
        now = time.monotonic()
        with self._lock:
            if self._popular_cache and self._popular_cache[0] > now:
                return self._popular_cache[1][:limit]

        html = self._get_html(f"{self.settings.ptt_base_url}/bbs/hotboards.html")
        boards = self.parse_popular_page(html)

        with self._lock:
            self._popular_cache = (now + 600, boards)
            self._remember_boards(boards)
        return boards[:limit]

    def search_boards(self, query: str, limit: int = 30) -> list[BoardOptionData]:
        normalized_query = query.strip().casefold()
        if not normalized_query:
            return self.get_popular_boards(limit=limit)

        candidates: dict[str, BoardOptionData] = {}
        for board in self.get_popular_boards(limit=200):
            candidates[board.board.casefold()] = board

        with self._lock:
            for board in self._known_boards.values():
                candidates[board.board.casefold()] = board

        matched = [
            board
            for board in candidates.values()
            if self._matches_query(board, normalized_query)
        ]

        normalized_board = normalize_board_name(query)
        normalized_key = normalized_board.casefold()
        is_alias = normalized_key != query.strip().casefold()
        if is_alias and normalized_key not in {board.board.casefold() for board in matched}:
            valid, _message = self.crawler.validate_board(normalized_board)
            if valid:
                exact = BoardOptionData(
                    board=normalized_board,
                    category="已驗證看板",
                    title="由 PTT 最新文章頁即時驗證",
                    popularity=None,
                    source="exact",
                )
                matched.append(exact)
                with self._lock:
                    self._known_boards[normalized_key] = exact

        matched.sort(key=lambda item: self._sort_key(item, normalized_query))
        return matched[:limit]

    def get_category(self, category_id: int) -> BoardCategoryData:
        if category_id < 1:
            raise BoardDirectoryError("分類編號不正確")

        now = time.monotonic()
        with self._lock:
            cached = self._category_cache.get(category_id)
            if cached and cached[0] > now:
                return cached[1]

        html = self._get_html(f"{self.settings.ptt_base_url}/cls/{category_id}")
        category = self.parse_category_page(html, category_id=category_id)

        boards = [
            BoardOptionData(
                board=entry.board or "",
                category=entry.category,
                title=entry.description,
                popularity=entry.popularity,
                source="category",
            )
            for entry in category.entries
            if entry.kind == "board" and entry.board
        ]

        with self._lock:
            self._category_cache[category_id] = (now + 3600, category)
            self._remember_boards(boards)
        return category

    def _get_html(self, url: str) -> str:
        try:
            with httpx.Client(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; PttAlertHub/1.1; "
                        "+https://github.com/)"
                    ),
                    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                },
                cookies={"over18": "1"},
                follow_redirects=True,
                timeout=self.settings.ptt_timeout_seconds,
                transport=httpx.HTTPTransport(retries=2),
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as error:
            raise BoardDirectoryError(f"讀取 PTT 看板目錄失敗：{error}") from error

    def _remember_boards(self, boards: list[BoardOptionData]) -> None:
        for board in boards:
            self._known_boards[board.board.casefold()] = board

    @staticmethod
    def _matches_query(board: BoardOptionData, query: str) -> bool:
        searchable = " ".join(
            (
                board.board,
                board.category,
                board.title,
                *BOARD_SEARCH_KEYWORDS.get(board.board, ()),
            )
        ).casefold()
        return query in searchable

    @staticmethod
    def _sort_key(board: BoardOptionData, query: str) -> tuple[int, int, str]:
        board_name = board.board.casefold()
        exact_rank = 0 if board_name == query else 1 if board_name.startswith(query) else 2
        popularity_rank = -(board.popularity or 0)
        return exact_rank, popularity_rank, board_name

    @staticmethod
    def parse_popular_page(html: str) -> list[BoardOptionData]:
        soup = BeautifulSoup(html, "html.parser")
        boards: list[BoardOptionData] = []
        seen: set[str] = set()

        links = soup.select('.b-list-container .b-ent a[href^="/bbs/"]')
        if not links:
            links = soup.select('div.b-ent a[href^="/bbs/"]')
        if not links:
            links = soup.select('a[href^="/bbs/"]')

        for link in links:
            href = link.get("href")
            if not isinstance(href, str):
                continue
            match = BOARD_LINK_PATTERN.match(href)
            if not match:
                continue

            board = unquote(match.group(1))
            if board.casefold() in seen:
                continue

            raw_text = link.get_text(" ", strip=True)
            popularity, category, title = BoardDirectoryService._parse_board_metadata(
                raw_text,
                board,
            )
            boards.append(
                BoardOptionData(
                    board=board,
                    category=category,
                    title=title,
                    popularity=popularity,
                    source="popular",
                )
            )
            seen.add(board.casefold())

        boards.sort(key=lambda item: (-(item.popularity or 0), item.board.casefold()))
        return boards

    @staticmethod
    def parse_category_page(html: str, *, category_id: int) -> BoardCategoryData:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else f"分類 {category_id}"
        entries: list[BoardDirectoryEntryData] = []
        seen: set[tuple[str, str]] = set()

        links = soup.select(".b-list-container .b-ent a[href]")
        if not links:
            links = soup.select("div.b-ent a[href]")
        if not links:
            links = soup.select("a[href]")

        for link in links:
            href = link.get("href")
            if not isinstance(href, str):
                continue

            category_match = CATEGORY_LINK_PATTERN.match(href)
            if category_match:
                child_id = int(category_match.group(1))
                if child_id == category_id:
                    continue
                raw_text = link.get_text(" ", strip=True)
                if not raw_text:
                    continue
                name, description = BoardDirectoryService._parse_category_metadata(raw_text)
                key = ("category", str(child_id))
                if key in seen:
                    continue
                entries.append(
                    BoardDirectoryEntryData(
                        kind="category",
                        name=name,
                        description=description,
                        category_id=child_id,
                    )
                )
                seen.add(key)
                continue

            board_match = BOARD_LINK_PATTERN.match(href)
            if not board_match:
                continue

            board = unquote(board_match.group(1))
            key = ("board", board.casefold())
            if key in seen:
                continue
            raw_text = link.get_text(" ", strip=True)
            popularity, category, description = BoardDirectoryService._parse_board_metadata(
                raw_text,
                board,
            )
            entries.append(
                BoardDirectoryEntryData(
                    kind="board",
                    name=board,
                    description=description,
                    board=board,
                    category=category,
                    popularity=popularity,
                )
            )
            seen.add(key)

        return BoardCategoryData(
            category_id=category_id,
            title=title,
            entries=entries,
        )

    @staticmethod
    def _parse_board_metadata(raw_text: str, board: str) -> tuple[int | None, str, str]:
        tokens = raw_text.split()
        if tokens and tokens[0].casefold() == board.casefold():
            tokens = tokens[1:]

        popularity: int | None = None
        if tokens:
            numeric = tokens[0].replace(",", "")
            if numeric.isdigit():
                popularity = int(numeric)
                tokens = tokens[1:]

        category = tokens[0] if tokens else ""
        title = " ".join(tokens[1:]) if len(tokens) > 1 else ""
        return popularity, category, title

    @staticmethod
    def _parse_category_metadata(raw_text: str) -> tuple[str, str]:
        tokens = raw_text.split()
        if not tokens:
            return "未命名分類", ""
        return tokens[0], " ".join(tokens[1:])


board_directory_service = BoardDirectoryService()
