import { useEffect, useState } from 'react';

import { api } from '../api/client';
import { Feedback, LoadingState } from '../components/Feedback';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import type { BoardCrawlSnapshot, CrawlRun } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

export function RunsPage() {
  const [runs, setRuns] = useState<CrawlRun[]>([]);
  const [snapshots, setSnapshots] = useState<BoardCrawlSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadRuns = async () => {
    setLoading(true);
    setError('');
    try {
      const [latestRuns, latestSnapshots] = await Promise.all([
        api.getRuns(),
        api.getLatestCrawlResults(),
      ]);
      setRuns(latestRuns);
      setSnapshots(latestSnapshots);
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
        description="查看各看板最後一次成功抓取的文章，以及每次排程的掃描數量、命中結果與錯誤。"
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
        <>
          <section className="c-card p-runs__latest">
            <div className="c-card__header">
              <div>
                <span className="c-card__eyebrow">LATEST SNAPSHOT</span>
                <h2 className="c-card__title">最新抓取結果</h2>
              </div>
              <span className="c-count-pill">{snapshots.length}</span>
            </div>
            <p className="p-runs__snapshot-note">
              每個看板只保留最後一次成功抓取的快照；下一次成功後會直接覆蓋，不會累積每 30 秒的完整明細。
            </p>

            {snapshots.length === 0 ? (
              <div className="c-empty-state">尚無成功抓取的看板結果。</div>
            ) : (
              <div className="c-crawl-snapshot-list">
                {snapshots.map((snapshot, index) => (
                  <details className="c-crawl-snapshot" key={snapshot.board} open={index === 0}>
                    <summary className="c-crawl-snapshot__summary">
                      <span className="c-crawl-snapshot__identity">
                        <span className="c-board-tag">{snapshot.board}</span>
                        <strong>{snapshot.articles_count} 篇文章</strong>
                      </span>
                      <small>抓取於 {formatDateTime(snapshot.fetched_at)}</small>
                    </summary>

                    {snapshot.articles.length === 0 ? (
                      <div className="c-empty-state">這次抓取沒有取得可顯示的文章。</div>
                    ) : (
                      <ol className="c-crawl-article-list">
                        {snapshot.articles.map((article) => (
                          <li className="c-crawl-article" key={article.article_key}>
                            <a href={article.url} target="_blank" rel="noreferrer">
                              {article.title}
                            </a>
                            <span className="c-crawl-article__meta">
                              {article.author || '未知作者'}
                              <span aria-hidden="true">・</span>
                              {article.ptt_date || (article.published_at ? formatDateTime(article.published_at) : '未知日期')}
                            </span>
                          </li>
                        ))}
                      </ol>
                    )}
                  </details>
                ))}
              </div>
            )}
          </section>

          <section className="c-card c-table-card p-runs__history">
            <div className="c-card__header p-runs__history-header">
              <div>
                <span className="c-card__eyebrow">RUN HISTORY</span>
                <h2 className="c-card__title">執行統計</h2>
              </div>
            </div>
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
        </>
      )}
    </div>
  );
}
