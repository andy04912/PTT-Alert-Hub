import { useEffect, useState } from 'react';

import { api } from '../api/client';
import { Feedback, LoadingState } from '../components/Feedback';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import type { CrawlRun, DashboardStats } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

interface DashboardPageProps {
  isAdmin: boolean;
}

export function DashboardPage({ isAdmin }: DashboardPageProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null,
  );

  const loadDashboard = async () => {
    try {
      setStats(await api.getDashboard());
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDashboard();
  }, []);

  const handleRun = async () => {
    setRunning(true);
    setFeedback(null);
    try {
      const run: CrawlRun = await api.runCrawl();
      const type = run.status === 'success' ? 'success' : 'error';
      setFeedback({
        type,
        message: `爬取完成：掃描 ${run.articles_scanned} 篇，命中 ${run.matches_count} 篇。${
          run.error_message ? ` ${run.error_message}` : ''
        }`,
      });
      await loadDashboard();
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="p-dashboard">
      <PageHeader
        eyebrow="OVERVIEW"
        title="個人監控總覽"
        description="查看你的規則、命中數量與系統排程狀態。"
        actions={
          isAdmin ? (
            <button className="c-button c-button--primary" disabled={running} onClick={handleRun}>
              {running ? '爬取中…' : '立即爬取'}
            </button>
          ) : undefined
        }
      />

      {feedback && <Feedback type={feedback.type} message={feedback.message} />}

      <section className="p-dashboard__stats" aria-label="統計資料">
        <article className="c-stat-card">
          <span className="c-stat-card__label">啟用規則</span>
          <strong className="c-stat-card__value">{stats?.enabled_rules ?? 0}</strong>
          <small className="c-stat-card__meta">共 {stats?.total_rules ?? 0} 條個人規則</small>
        </article>
        <article className="c-stat-card">
          <span className="c-stat-card__label">命中文章</span>
          <strong className="c-stat-card__value">{stats?.seen_articles ?? 0}</strong>
          <small className="c-stat-card__meta">同一篇文章只計算一次</small>
        </article>
        <article className="c-stat-card">
          <span className="c-stat-card__label">規則命中</span>
          <strong className="c-stat-card__value">{stats?.total_matches ?? 0}</strong>
          <small className="c-stat-card__meta">同篇文章可命中多條規則</small>
        </article>
        <article className="c-stat-card">
          <span className="c-stat-card__label">下次排程</span>
          <strong className="c-stat-card__value c-stat-card__value--date">
            {formatDateTime(stats?.next_run_at)}
          </strong>
          <small className="c-stat-card__meta">
            {stats?.scheduler_running ? 'Crawler Worker 運作中' : 'Crawler Worker 未啟動'}
          </small>
        </article>
      </section>

      <section className="c-card">
        <div className="c-card__header">
          <div>
            <span className="c-card__eyebrow">LAST RUN</span>
            <h2 className="c-card__title">系統最近一次爬取</h2>
          </div>
          {stats?.last_run && <StatusBadge status={stats.last_run.status} />}
        </div>

        {stats?.last_run ? (
          <dl className="c-detail-grid">
            <div className="c-detail-grid__item">
              <dt>啟動方式</dt>
              <dd>{stats.last_run.trigger === 'manual' ? '手動' : '排程'}</dd>
            </div>
            <div className="c-detail-grid__item">
              <dt>開始時間</dt>
              <dd>{formatDateTime(stats.last_run.started_at)}</dd>
            </div>
            <div className="c-detail-grid__item">
              <dt>看板數</dt>
              <dd>{stats.last_run.boards_count}</dd>
            </div>
            <div className="c-detail-grid__item">
              <dt>掃描文章</dt>
              <dd>{stats.last_run.articles_scanned}</dd>
            </div>
            <div className="c-detail-grid__item">
              <dt>命中文章</dt>
              <dd>{stats.last_run.matches_count}</dd>
            </div>
            <div className="c-detail-grid__item">
              <dt>通知傳送</dt>
              <dd>{stats.last_run.notification_sent ? '已傳送' : '未傳送'}</dd>
            </div>
            {isAdmin && stats.last_run.error_message && (
              <div className="c-detail-grid__item c-detail-grid__item--full">
                <dt>訊息</dt>
                <dd>{stats.last_run.error_message}</dd>
              </div>
            )}
          </dl>
        ) : (
          <p className="c-empty-state">尚未執行過爬取。</p>
        )}
      </section>
    </div>
  );
}
