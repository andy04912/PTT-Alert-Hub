import type {
  ActionResponse,
  AppSetting,
  AppSettingPayload,
  BoardCategory,
  BoardOption,
  BoardValidationResponse,
  CrawlRun,
  DashboardStats,
  LoginResponse,
  Rule,
  RulePayload,
} from '../types';

const API_BASE_URL = '/api';
const TOKEN_KEY = 'ptt-alert-hub-token';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    clearStoredToken();
    window.dispatchEvent(new CustomEvent('auth-expired'));
  }

  if (!response.ok) {
    let message = `請求失敗（${response.status}）`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // 保留預設錯誤訊息。
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  getDashboard: () => request<DashboardStats>('/dashboard'),

  getRules: () => request<Rule[]>('/rules'),
  createRule: (payload: RulePayload) =>
    request<Rule>('/rules', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateRule: (ruleId: number, payload: RulePayload) =>
    request<Rule>(`/rules/${ruleId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteRule: (ruleId: number) =>
    request<void>(`/rules/${ruleId}`, {
      method: 'DELETE',
    }),
  validateBoard: (board: string) =>
    request<BoardValidationResponse>(`/rules/validate/${encodeURIComponent(board)}`),

  getPopularBoards: (limit = 50) =>
    request<BoardOption[]>(`/boards/popular?limit=${limit}`),
  searchBoards: (query: string, limit = 30) =>
    request<BoardOption[]>(
      `/boards/search?q=${encodeURIComponent(query)}&limit=${limit}`,
    ),
  getBoardCategory: (categoryId: number) =>
    request<BoardCategory>(`/boards/categories/${categoryId}`),

  getSettings: () => request<AppSetting>('/settings'),
  updateSettings: (payload: AppSettingPayload) =>
    request<AppSetting>('/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  testNotification: () =>
    request<ActionResponse>('/settings/test-notification', { method: 'POST' }),

  runCrawl: () => request<CrawlRun>('/crawl/run', { method: 'POST' }),
  getRuns: (limit = 50) => request<CrawlRun[]>(`/crawl/runs?limit=${limit}`),
};
