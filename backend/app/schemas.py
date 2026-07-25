from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.boards import normalize_board_name
from app.models import CrawlRunStatus, RuleMatchType


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    is_admin: bool
    created_at: datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("顯示名稱不可為空白")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    board: str = Field(min_length=1, max_length=60)
    match_type: RuleMatchType
    pattern: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    case_sensitive: bool = False

    @field_validator("name", "pattern")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不可為空白")
        return value

    @field_validator("board")
    @classmethod
    def validate_board(cls, value: str) -> str:
        value = normalize_board_name(value)
        if not value:
            raise ValueError("看板不可為空白")
        if not all(char.isalnum() or char in {"_", "-"} for char in value):
            raise ValueError("看板名稱只能包含英數字、底線或連字號")
        return value


class RuleCreate(RuleBase):
    pass


class RuleUpdate(RuleBase):
    pass


class RuleRead(RuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class AppSettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    interval_minutes: int
    pages_per_board: int
    notification_enabled: bool
    telegram_configured: bool
    timezone: str
    updated_at: datetime


class AppSettingUpdate(BaseModel):
    interval_minutes: int = Field(ge=1, le=1440)
    pages_per_board: int = Field(ge=1, le=10)
    notification_enabled: bool

    @model_validator(mode="after")
    def validate_high_frequency_settings(self) -> "AppSettingUpdate":
        if self.interval_minutes == 1 and self.pages_per_board > 2:
            raise ValueError("使用 1 分鐘頻率時，每個看板最多掃描 2 頁")
        return self


class BoardValidationResponse(BaseModel):
    board: str
    valid: bool
    message: str


class CrawlRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trigger: str
    status: CrawlRunStatus
    started_at: datetime
    finished_at: datetime | None
    boards_count: int
    articles_scanned: int
    matches_count: int
    notification_sent: bool
    error_message: str | None


class DashboardStats(BaseModel):
    enabled_rules: int
    total_rules: int
    seen_articles: int
    total_matches: int
    last_run: CrawlRunRead | None
    next_run_at: datetime | None
    scheduler_running: bool
    telegram_configured: bool


class ActionResponse(BaseModel):
    success: bool
    message: str


class BoardOptionRead(BaseModel):
    board: str
    category: str
    title: str
    popularity: int | None
    source: str


class BoardDirectoryEntryRead(BaseModel):
    kind: str
    name: str
    description: str
    board: str | None = None
    category_id: int | None = None
    category: str = ""
    popularity: int | None = None


class BoardCategoryRead(BaseModel):
    category_id: int
    title: str
    entries: list[BoardDirectoryEntryRead]
