import { useState, type PropsWithChildren } from 'react';
import { NavLink } from 'react-router-dom';

import type { User } from '../types';

interface AppShellProps extends PropsWithChildren {
  user: User;
  onLogout: () => void;
}

const navigationItems = [
  { to: '/', label: '總覽', icon: '◫', end: true, adminOnly: false },
  { to: '/rules', label: '通知規則', icon: '⌕', adminOnly: false },
  { to: '/matches', label: '命中紀錄', icon: '✓', adminOnly: false },
  { to: '/push', label: '推播通知', icon: '◉', adminOnly: false },
  { to: '/runs', label: '爬取紀錄', icon: '↻', adminOnly: true },
  { to: '/settings', label: '系統設定', icon: '⚙', adminOnly: true },
];

export function AppShell({ children, user, onLogout }: AppShellProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const visibleNavigationItems = navigationItems.filter(
    (item) => !item.adminOnly || user.is_admin,
  );

  return (
    <div className="l-app-shell">
      <aside
        className={`l-app-shell__sidebar ${mobileMenuOpen ? 'l-app-shell__sidebar--open' : ''}`}
      >
        <div className="c-brand">
          <div className="c-brand__mark">P</div>
          <div>
            <strong className="c-brand__name">PTT Alert Hub</strong>
            <span className="c-brand__caption">個人文章監控中心</span>
          </div>
        </div>

        <nav className="c-nav" aria-label="主要導覽">
          {visibleNavigationItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `c-nav__item ${isActive ? 'c-nav__item--active' : ''}`
              }
            >
              <span className="c-nav__icon" aria-hidden="true">
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <button className="c-button c-button--ghost c-button--full" type="button" onClick={onLogout}>
          登出
        </button>
      </aside>

      {mobileMenuOpen && (
        <button
          type="button"
          aria-label="關閉選單"
          className="l-app-shell__backdrop"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <div className="l-app-shell__content">
        <header className="l-app-shell__topbar">
          <button
            className="c-icon-button l-app-shell__menu-button"
            type="button"
            aria-label="開啟選單"
            onClick={() => setMobileMenuOpen(true)}
          >
            ☰
          </button>
          <span className="l-app-shell__topbar-title">{user.display_name}</span>
          <span className="c-live-dot">
            {user.is_admin ? '系統管理員' : '個人帳號'}
          </span>
        </header>
        <main className="l-app-shell__main">{children}</main>
      </div>
    </div>
  );
}
