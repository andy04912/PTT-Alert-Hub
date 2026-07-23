import { useEffect, useState, type FormEvent } from 'react';

import { api } from '../api/client';
import { BoardPicker } from '../components/BoardPicker';
import { EmptyState, Feedback, LoadingState } from '../components/Feedback';
import { PageHeader } from '../components/PageHeader';
import type { Rule, RulePayload } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

const emptyRule = (): RulePayload => ({
  name: '',
  board: '',
  match_type: 'title_keyword',
  pattern: '',
  enabled: true,
  case_sensitive: false,
});

function toPayload(rule: Rule): RulePayload {
  return {
    name: rule.name,
    board: rule.board,
    match_type: rule.match_type,
    pattern: rule.pattern,
    enabled: rule.enabled,
    case_sensitive: rule.case_sensitive,
  };
}

export function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [form, setForm] = useState<RulePayload>(emptyRule());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);

  const loadRules = async () => {
    try {
      setRules(await api.getRules());
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRules();
  }, []);

  const resetForm = () => {
    setForm(emptyRule());
    setEditingId(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setFeedback(null);

    try {
      if (editingId) {
        await api.updateRule(editingId, form);
        setFeedback({ type: 'success', message: '規則已更新。' });
      } else {
        await api.createRule(form);
        setFeedback({
          type: 'success',
          message: '規則已建立；系統只會通知規則建立後發布的新文章。',
        });
      }
      resetForm();
      await loadRules();
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (rule: Rule) => {
    setEditingId(rule.id);
    setForm(toPayload(rule));
    setFeedback(null);
    document.querySelector('.l-app-shell__main')?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (rule: Rule) => {
    if (!window.confirm(`確定刪除「${rule.name}」嗎？`)) {
      return;
    }

    try {
      await api.deleteRule(rule.id);
      if (editingId === rule.id) {
        resetForm();
      }
      setFeedback({ type: 'success', message: '規則已刪除。' });
      await loadRules();
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    }
  };

  const handleToggle = async (rule: Rule) => {
    try {
      await api.updateRule(rule.id, { ...toPayload(rule), enabled: !rule.enabled });
      await loadRules();
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    }
  };

  const handleValidateBoard = async () => {
    if (!form.board.trim()) {
      setFeedback({ type: 'error', message: '請先輸入看板名稱。' });
      return;
    }

    setValidating(true);
    setFeedback(null);
    try {
      const result = await api.validateBoard(form.board.trim());
      if (result.valid) {
        setForm((currentForm) => ({ ...currentForm, board: result.board }));
      }
      setFeedback({
        type: result.valid ? 'success' : 'error',
        message: result.message,
      });
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setValidating(false);
    }
  };

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="p-rules">
      <PageHeader
        eyebrow="RULES"
        title="通知規則"
        description="使用標題關鍵字或作者帳號比對最新文章；同一輪命中會合併成一則通知。"
      />

      {feedback && <Feedback type={feedback.type} message={feedback.message} />}

      <section className="p-rules__layout">
        <form className="c-card c-form" onSubmit={handleSubmit}>
          <div className="c-card__header">
            <div>
              <span className="c-card__eyebrow">{editingId ? 'EDIT' : 'NEW RULE'}</span>
              <h2 className="c-card__title">{editingId ? '編輯規則' : '新增規則'}</h2>
            </div>
            {editingId && (
              <button className="c-button c-button--ghost c-button--small" type="button" onClick={resetForm}>
                取消編輯
              </button>
            )}
          </div>

          <label className="c-field">
            <span className="c-field__label">規則名稱</span>
            <input
              className="c-input"
              placeholder="例如：Tech_Job 徵才"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
            />
          </label>

          <div className="c-field">
            <span className="c-field__label">PTT 看板</span>
            <BoardPicker
              value={form.board}
              disabled={saving || validating}
              onChange={(board) => setForm({ ...form, board })}
            />
            <div className="c-field__actions">
              <button
                className="c-button c-button--ghost c-button--small"
                type="button"
                disabled={validating || !form.board.trim()}
                onClick={handleValidateBoard}
              >
                {validating ? '驗證中…' : '驗證目前看板'}
              </button>
            </div>
            <small className="c-field__hint">
              可搜尋熱門或已瀏覽過的看板，也能逐層瀏覽 PTT 官方分類目錄。找不到時仍可直接輸入，儲存規則時會再次驗證。
            </small>
          </div>

          <label className="c-field">
            <span className="c-field__label">比對方式</span>
            <select
              className="c-select"
              value={form.match_type}
              onChange={(event) =>
                setForm({
                  ...form,
                  match_type: event.target.value as RulePayload['match_type'],
                })
              }
            >
              <option value="title_keyword">標題包含關鍵字</option>
              <option value="author">作者帳號完全符合</option>
            </select>
          </label>

          <label className="c-field">
            <span className="c-field__label">
              {form.match_type === 'author' ? '作者帳號' : '標題關鍵字'}
            </span>
            <input
              className="c-input"
              placeholder={form.match_type === 'author' ? 'andy123' : '徵才'}
              value={form.pattern}
              onChange={(event) => setForm({ ...form, pattern: event.target.value })}
              required
            />
          </label>

          <div className="c-form__options">
            <label className="c-switch-row">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
              />
              <span>
                <strong>啟用規則</strong>
                <small>停用後不會建立新命中。</small>
              </span>
            </label>
            <label className="c-switch-row">
              <input
                type="checkbox"
                checked={form.case_sensitive}
                onChange={(event) => setForm({ ...form, case_sensitive: event.target.checked })}
              />
              <span>
                <strong>區分英文大小寫</strong>
                <small>中文關鍵字不受影響。</small>
              </span>
            </label>
          </div>

          <button className="c-button c-button--primary c-button--full" disabled={saving}>
            {saving ? '儲存中…' : editingId ? '儲存變更' : '建立規則'}
          </button>
        </form>

        <section className="c-card p-rules__list">
          <div className="c-card__header">
            <div>
              <span className="c-card__eyebrow">ACTIVE WATCHES</span>
              <h2 className="c-card__title">目前規則</h2>
            </div>
            <span className="c-count-pill">{rules.length}</span>
          </div>

          {rules.length === 0 ? (
            <EmptyState message="尚未建立任何規則。" />
          ) : (
            <div className="c-rule-list">
              {rules.map((rule) => (
                <article className={`c-rule-item ${!rule.enabled ? 'c-rule-item--disabled' : ''}`} key={rule.id}>
                  <div className="c-rule-item__main">
                    <div className="c-rule-item__heading">
                      <span className="c-board-tag">{rule.board}</span>
                      <h3 className="c-rule-item__title">{rule.name}</h3>
                    </div>
                    <p className="c-rule-item__condition">
                      {rule.match_type === 'author' ? '作者等於' : '標題包含'}
                      <strong>「{rule.pattern}」</strong>
                    </p>
                    <small className="c-rule-item__meta">
                      建立於 {formatDateTime(rule.created_at)}
                      {rule.case_sensitive ? '・區分大小寫' : ''}
                    </small>
                  </div>

                  <div className="c-rule-item__actions">
                    <label className="c-toggle" title={rule.enabled ? '停用' : '啟用'}>
                      <input
                        type="checkbox"
                        checked={rule.enabled}
                        onChange={() => void handleToggle(rule)}
                      />
                      <span className="c-toggle__track" />
                    </label>
                    <button className="c-button c-button--ghost c-button--small" type="button" onClick={() => handleEdit(rule)}>
                      編輯
                    </button>
                    <button
                      className="c-button c-button--danger-ghost c-button--small"
                      type="button"
                      onClick={() => void handleDelete(rule)}
                    >
                      刪除
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>
    </div>
  );
}
