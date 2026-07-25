import { useEffect, useState } from 'react';

import { api } from '../api/client';
import { Feedback, LoadingState } from '../components/Feedback';
import { PageHeader } from '../components/PageHeader';
import type { ArticleMatch } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

export function MatchesPage() {
  const [matches, setMatches] = useState<ArticleMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadMatches = async () => {
    setLoading(true);
    setError('');
    try {
      setMatches(await api.getMatches());
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadMatches();
  }, []);

  return (
    <div className="p-runs">
      <PageHeader
        eyebrow="MATCHES"
        title="我的命中紀錄"
        description="只顯示屬於你個人規則的命中文章。"
        actions={
          <button className="c-button c-button--secondary" type="button" onClick={() => void loadMatches()}>
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
                  <th>命中時間</th>
                  <th>看板</th>
                  <th>文章</th>
                  <th>作者</th>
                  <th>規則</th>
                  <th>通知狀態</th>
                </tr>
              </thead>
              <tbody>
                {matches.map((match) => (
                  <tr key={match.id}>
                    <td>{formatDateTime(match.matched_at)}</td>
                    <td>{match.board}</td>
                    <td className="c-table__message">
                      <a href={match.url} target="_blank" rel="noreferrer">
                        {match.title}
                      </a>
                    </td>
                    <td>{match.author}</td>
                    <td>{match.rule_name}</td>
                    <td>{match.notified_at ? '已通知' : '等待 PWA 推播'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {matches.length === 0 && <div className="c-empty-state">目前尚無命中文章。</div>}
        </section>
      )}
    </div>
  );
}
