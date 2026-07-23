from __future__ import annotations

BOARD_ALIASES: dict[str, str] = {
    "taichung": "TaichungBun",
    "taichungbun": "TaichungBun",
    "台中": "TaichungBun",
    "台中板": "TaichungBun",
    "tech_job": "Tech_Job",
    "techjob": "Tech_Job",
    "科技工作": "Tech_Job",
    "科技工作板": "Tech_Job",
}

BOARD_SEARCH_KEYWORDS: dict[str, tuple[str, ...]] = {
    "TaichungBun": ("台中", "台中板", "台中版", "taichung"),
    "Tech_Job": ("科技工作", "科技業", "徵才", "工作", "tech job"),
}


def normalize_board_name(board: str) -> str:
    normalized = board.strip()
    if not normalized:
        return normalized
    return BOARD_ALIASES.get(normalized.casefold(), normalized)
