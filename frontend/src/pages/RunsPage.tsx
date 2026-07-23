import { useEffect, useState } from 'react';

import { api } from '../api/client';
import { Feedback, LoadingState } from '../components/Feedback';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import type { CrawlRun } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

export function RunsPage() {
  const [runs, setRuns] = useState<CrawlRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadRuns = async () => {
    setLoading(true);
    setError('');
    try {
      setRuns(await api.getRuns());
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRuns();
  }, []);

  return (
    <div className="p-runs">
      <PageHeader
        eyebrow="HISTORY"
        title="爬取紀錄"
        description="查看每次排程或手動爬取的掃描數量、命中結果與錯誤。"
        actions={
          <button className="c-button c-button--secondary" type="button" onClick={() => void loadRuns()}>
            重新整理
          </button>
        }
      />

      {error && <Feedback type="error" message={error} />}
      {loading ? (
        <LoadingState />
      ) : (
        <section className="c-card c-table-card">
          <div className="c-table-wrap">
            <table className="c-table">
              <thead>
                <tr>
                  <th>狀態</th>
                  <th>開始時間</th>
                  <th>來源</th>
                  <th>看板</th>
                  <th>掃描</th>
                  <th>命中</th>
                  <th>通知</th>
                  <th>訊息</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td><StatusBadge status={run.status} /></td>
                    <td>{formatDateTime(run.started_at)}</td>
                    <td>{run.trigger === 'manual' ? '手動' : '排程'}</td>
                    <td>{run.boards_count}</td>
                    <td>{run.articles_scanned}</td>
                    <td>{run.matches_count}</td>
                    <td>{run.notification_sent ? '已傳送' : '—'}</td>
                    <td className="c-table__message">{run.error_message || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {runs.length === 0 && <div className="c-empty-state">尚無爬取紀錄。</div>}
        </section>
      )}
    </div>
  );
}
