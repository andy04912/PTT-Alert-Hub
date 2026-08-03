import { useEffect, useState, type FormEvent } from 'react';

import { api } from '../api/client';
import { Feedback, LoadingState } from '../components/Feedback';
import { PageHeader } from '../components/PageHeader';
import type { AppSettingPayload } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

const defaultForm: AppSettingPayload = {
  interval_seconds: 30,
  pages_per_board: 1,
  notification_enabled: true,
};

export function SettingsPage() {
  const [form, setForm] = useState<AppSettingPayload>(defaultForm);
  const [telegramConfigured, setTelegramConfigured] = useState(false);
  const [timezone, setTimezone] = useState('Asia/Taipei');
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const setting = await api.getSettings();
        setForm({
          interval_seconds: setting.interval_seconds,
          pages_per_board: setting.pages_per_board,
          notification_enabled: setting.notification_enabled,
        });
        setTelegramConfigured(setting.telegram_configured);
        setTimezone(setting.timezone);
        setUpdatedAt(setting.updated_at);
      } catch (error) {
        setFeedback({ type: 'error', message: getErrorMessage(error) });
      } finally {
        setLoading(false);
      }
    };

    void loadSettings();
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      const setting = await api.updateSettings(form);
      setForm({
        interval_seconds: setting.interval_seconds,
        pages_per_board: setting.pages_per_board,
        notification_enabled: setting.notification_enabled,
      });
      setUpdatedAt(setting.updated_at);
      setFeedback({
        type: 'success',
        message: '設定已儲存，Crawler Worker 會在約 10 秒內套用新排程。',
      });
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setSaving(false);
    }
  };

  const handleTestNotification = async () => {
    setTesting(true);
    setFeedback(null);
    try {
      const result = await api.testNotification();
      setFeedback({ type: 'success', message: result.message });
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="p-settings">
      <PageHeader
        eyebrow="SETTINGS"
        title="系統設定"
        description="調整爬取頻率、每個看板的掃描頁數與通知開關。"
      />

      {feedback && <Feedback type={feedback.type} message={feedback.message} />}

      <section className="p-settings__grid">
        <form className="c-card c-form" onSubmit={handleSubmit}>
          <div className="c-card__header">
            <div>
              <span className="c-card__eyebrow">SCHEDULER</span>
              <h2 className="c-card__title">爬取排程</h2>
            </div>
          </div>

          <label className="c-field">
            <span className="c-field__label">執行間隔（秒）</span>
            <input
              className="c-input"
              type="number"
              min={30}
              max={86400}
              step={10}
              value={form.interval_seconds}
              onChange={(event) =>
                setForm({ ...form, interval_seconds: Number(event.target.value) })
              }
              required
            />
            <small className="c-field__hint">
              最低 30 秒。低於 60 秒時每個看板只能掃描最新 1 頁；若上一輪尚未完成，系統會略過重疊執行。
            </small>
          </label>

          <label className="c-field">
            <span className="c-field__label">每個看板掃描頁數</span>
            <input
              className="c-input"
              type="number"
              min={1}
              max={form.interval_seconds < 60 ? 1 : form.interval_seconds === 60 ? 2 : 10}
              value={form.pages_per_board}
              onChange={(event) =>
                setForm({ ...form, pages_per_board: Number(event.target.value) })
              }
              required
            />
            <small className="c-field__hint">頁數越多，請求量與執行時間越高。</small>
          </label>

          <label className="c-switch-row c-switch-row--panel">
            <input
              type="checkbox"
              checked={form.notification_enabled}
              onChange={(event) =>
                setForm({ ...form, notification_enabled: event.target.checked })
              }
            />
            <span>
              <strong>啟用通知</strong>
              <small>停用期間的命中會保留，重新啟用後再送出。</small>
            </span>
          </label>

          <button className="c-button c-button--primary c-button--full" disabled={saving}>
            {saving ? '儲存中…' : '儲存設定'}
          </button>
          <small className="c-form__footnote">
            時區：{timezone}・最後更新：{formatDateTime(updatedAt)}
          </small>
        </form>

        <section className="c-card">
          <div className="c-card__header">
            <div>
              <span className="c-card__eyebrow">TELEGRAM</span>
              <h2 className="c-card__title">通知管道</h2>
            </div>
            <span className={`c-config-status ${telegramConfigured ? 'c-config-status--ready' : ''}`}>
              {telegramConfigured ? '已設定' : '未設定'}
            </span>
          </div>

          <div className="c-instruction">
            <p>
              Telegram 的 Bot Token 與 Chat ID 透過伺服器環境變數設定，後台不回傳敏感資訊。
            </p>
            <ol className="c-instruction__steps">
              <li>使用 BotFather 建立 Bot 並取得 Token。</li>
              <li>先傳訊息給 Bot，再透過 getUpdates 取得 Chat ID。</li>
              <li>填入 .env 後重新啟動 backend 與 crawler-worker。</li>
            </ol>
            <div className="c-code-block">
              <code>TELEGRAM_BOT_TOKEN=...</code>
              <code>TELEGRAM_CHAT_ID=...</code>
            </div>
          </div>

          <button
            className="c-button c-button--secondary c-button--full"
            type="button"
            disabled={testing || !telegramConfigured}
            onClick={handleTestNotification}
          >
            {testing ? '傳送中…' : '傳送測試通知'}
          </button>
        </section>
      </section>
    </div>
  );
}
