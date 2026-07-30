import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';
import { Feedback } from '../components/Feedback';
import type { LoginResponse } from '../types';
import { getErrorMessage } from '../utils';

interface LoginPageProps {
  onAuthenticated: (response: LoginResponse, rememberMe: boolean) => void;
}

export function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      onAuthenticated(await api.login(email, password, rememberMe), rememberMe);
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
          <span className="p-login__eyebrow">PERSONAL ALERTS</span>
          <h1 className="p-login__title">登入你的監控中心</h1>
          <p className="p-login__description">
            每個帳號都有獨立的看板規則與命中紀錄，不會看到其他使用者的資料。
          </p>
        </div>

        <form className="c-form" onSubmit={handleSubmit}>
          {error && <Feedback type="error" message={error} />}
          <label className="c-field">
            <span className="c-field__label">Email</span>
            <input
              className="c-input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label className="c-field">
            <span className="c-field__label">密碼</span>
            <input
              className="c-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <label className="c-switch-row">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(event) => setRememberMe(event.target.checked)}
            />
            <span>
              <strong>記住我</strong>
              <small>在這台裝置保持登入 30 天。</small>
            </span>
          </label>
          <button className="c-button c-button--primary c-button--full" disabled={loading}>
            {loading ? '登入中…' : '登入'}
          </button>
          <p className="p-login__description">
            還沒有帳號？ <Link to="/register">建立個人帳號</Link>
          </p>
        </form>
      </section>

      <aside className="p-login__visual" aria-hidden="true">
        <div className="p-login__visual-card p-login__visual-card--first">
          <span>Tech_Job</span>
          <strong>標題包含「徵才」</strong>
          <em>個人規則</em>
        </div>
        <div className="p-login__visual-card p-login__visual-card--second">
          <span>TaichungBun</span>
          <strong>作者等於 andy123</strong>
          <em>等待新文章</em>
        </div>
      </aside>
    </main>
  );
}
