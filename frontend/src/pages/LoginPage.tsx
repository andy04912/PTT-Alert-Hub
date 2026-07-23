import { useState, type FormEvent } from 'react';

import { api } from '../api/client';
import { Feedback } from '../components/Feedback';
import { getErrorMessage } from '../utils';

interface LoginPageProps {
  onLogin: (token: string) => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await api.login(username, password);
      onLogin(response.access_token);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="p-login">
      <section className="p-login__panel">
        <div className="c-brand c-brand--login">
          <div className="c-brand__mark">P</div>
          <div>
            <strong className="c-brand__name">PTT Alert Hub</strong>
            <span className="c-brand__caption">只追蹤你真正關心的文章</span>
          </div>
        </div>

        <div className="p-login__intro">
          <span className="p-login__eyebrow">ADMIN CONSOLE</span>
          <h1 className="p-login__title">登入監控後台</h1>
          <p className="p-login__description">
            設定看板、標題關鍵字與作者帳號，系統會定時爬取並合併推送命中文章。
          </p>
        </div>

        <form className="c-form" onSubmit={handleSubmit}>
          {error && <Feedback type="error" message={error} />}
          <label className="c-field">
            <span className="c-field__label">管理員帳號</span>
            <input
              className="c-input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="c-field">
            <span className="c-field__label">管理員密碼</span>
            <input
              className="c-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button className="c-button c-button--primary c-button--full" disabled={loading}>
            {loading ? '登入中…' : '登入'}
          </button>
        </form>
      </section>

      <aside className="p-login__visual" aria-hidden="true">
        <div className="p-login__visual-card p-login__visual-card--first">
          <span>Tech_Job</span>
          <strong>標題包含「徵才」</strong>
          <em>已啟用</em>
        </div>
        <div className="p-login__visual-card p-login__visual-card--second">
          <span>Taichung</span>
          <strong>作者等於 andy123</strong>
          <em>等待新文章</em>
        </div>
      </aside>
    </main>
  );
}
