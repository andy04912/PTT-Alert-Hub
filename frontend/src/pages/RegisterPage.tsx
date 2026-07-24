import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { api } from '../api/client';
import { Feedback } from '../components/Feedback';
import type { LoginResponse } from '../types';
import { getErrorMessage } from '../utils';

interface RegisterPageProps {
  onAuthenticated: (response: LoginResponse) => void;
}

export function RegisterPage({ onAuthenticated }: RegisterPageProps) {
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('兩次輸入的密碼不一致');
      return;
    }

    setLoading(true);
    try {
      onAuthenticated(await api.register(email, displayName, password));
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
            <span className="c-brand__caption">建立你的個人文章雷達</span>
          </div>
        </div>

        <div className="p-login__intro">
          <span className="p-login__eyebrow">CREATE ACCOUNT</span>
          <h1 className="p-login__title">建立個人帳號</h1>
          <p className="p-login__description">
            註冊後即可建立自己的看板、關鍵字與作者監控規則。
          </p>
        </div>

        <form className="c-form" onSubmit={handleSubmit}>
          {error && <Feedback type="error" message={error} />}
          <label className="c-field">
            <span className="c-field__label">顯示名稱</span>
            <input
              className="c-input"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              autoComplete="name"
              maxLength={80}
              required
            />
          </label>
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
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              required
            />
          </label>
          <label className="c-field">
            <span className="c-field__label">確認密碼</span>
            <input
              className="c-input"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              required
            />
          </label>
          <button className="c-button c-button--primary c-button--full" disabled={loading}>
            {loading ? '建立中…' : '建立帳號'}
          </button>
          <p className="p-login__description">
            已經有帳號？ <Link to="/login">返回登入</Link>
          </p>
        </form>
      </section>

      <aside className="p-login__visual" aria-hidden="true">
        <div className="p-login__visual-card p-login__visual-card--first">
          <span>你的規則</span>
          <strong>只屬於你的監控清單</strong>
          <em>資料隔離</em>
        </div>
        <div className="p-login__visual-card p-login__visual-card--second">
          <span>即將支援</span>
          <strong>PWA 安裝與推播通知</strong>
          <em>下一階段</em>
        </div>
      </aside>
    </main>
  );
}
