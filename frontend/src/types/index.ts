export type RuleMatchType = 'title_keyword' | 'author';
export type RuleConditionOperator = 'title_contains' | 'title_not_contains';
export type CrawlRunStatus = 'running' | 'success' | 'failed' | 'skipped';

export interface User {
  id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
  created_at: string;
}

export interface RuleCondition {
  operator: RuleConditionOperator;
  pattern: string;
}

export interface Rule {
  id: number;
  name: string;
  board: string;
  match_type: RuleMatchType;
  pattern: string;
  additional_conditions: RuleCondition[];
  enabled: boolean;
  case_sensitive: boolean;
  created_at: string;
  updated_at: string;
}

export type RulePayload = Omit<Rule, 'id' | 'created_at' | 'updated_at'>;

export interface ArticleMatch {
  id: number;
  rule_id: number;
  rule_name: string;
  board: string;
  title: string;
  author: string;
  url: string;
  published_at: string | null;
  matched_at: string;
  notified_at: string | null;
  push_notified_at: string | null;
}

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
  interval_seconds: number;
  pages_per_board: number;
  notification_enabled: boolean;
  telegram_configured: boolean;
  timezone: string;
  updated_at: string;
}

export interface AppSettingPayload {
  interval_seconds: number;
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

export interface PushStatus {
  configured: boolean;
  public_key: string | null;
  subscription_count: number;
  enabled_subscription_count: number;
}

export interface PushDevice {
  id: number;
  device_name: string;
  user_agent: string;
  enabled: boolean;
  failure_count: number;
  last_success_at: string | null;
  last_failure_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PushSubscriptionPayload {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  device_name: string;
  user_agent: string;
}

export interface PushActionResponse extends ActionResponse {
  delivered: number;
  disabled: number;
  failed: number;
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
