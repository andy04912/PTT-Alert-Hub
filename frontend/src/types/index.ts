export type RuleMatchType = 'title_keyword' | 'author';
export type CrawlRunStatus = 'running' | 'success' | 'failed' | 'skipped';

export interface User {
  id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
  created_at: string;
}

export interface Rule {
  id: number;
  name: string;
  board: string;
  match_type: RuleMatchType;
  pattern: string;
  enabled: boolean;
  case_sensitive: boolean;
  created_at: string;
  updated_at: string;
}

export type RulePayload = Omit<Rule, 'id' | 'created_at' | 'updated_at'>;

export interface CrawlRun {
  id: number;
  trigger: string;
  status: CrawlRunStatus;
  started_at: string;
  finished_at: string | null;
  boards_count: number;
  articles_scanned: number;
  matches_count: number;
  notification_sent: boolean;
  error_message: string | null;
}

export interface DashboardStats {
  enabled_rules: number;
  total_rules: number;
  seen_articles: number;
  total_matches: number;
  last_run: CrawlRun | null;
  next_run_at: string | null;
  scheduler_running: boolean;
  telegram_configured: boolean;
}

export interface AppSetting {
  interval_minutes: number;
  pages_per_board: number;
  notification_enabled: boolean;
  telegram_configured: boolean;
  timezone: string;
  updated_at: string;
}

export interface AppSettingPayload {
  interval_minutes: number;
  pages_per_board: number;
  notification_enabled: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ActionResponse {
  success: boolean;
  message: string;
}

export interface BoardValidationResponse {
  board: string;
  valid: boolean;
  message: string;
}

export type BoardSource = 'popular' | 'category' | 'exact';
export type BoardDirectoryEntryKind = 'board' | 'category';

export interface BoardOption {
  board: string;
  category: string;
  title: string;
  popularity: number | null;
  source: BoardSource;
}

export interface BoardDirectoryEntry {
  kind: BoardDirectoryEntryKind;
  name: string;
  description: string;
  board: string | null;
  category_id: number | null;
  category: string;
  popularity: number | null;
}

export interface BoardCategory {
  category_id: number;
  title: string;
  entries: BoardDirectoryEntry[];
}
