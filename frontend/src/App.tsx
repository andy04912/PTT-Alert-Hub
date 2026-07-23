import { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { clearStoredToken, getStoredToken, setStoredToken } from './api/client';
import { AppShell } from './components/AppShell';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { RulesPage } from './pages/RulesPage';
import { RunsPage } from './pages/RunsPage';
import { SettingsPage } from './pages/SettingsPage';

export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getStoredToken()));

  useEffect(() => {
    const handleExpired = () => setAuthenticated(false);
    window.addEventListener('auth-expired', handleExpired);
    return () => window.removeEventListener('auth-expired', handleExpired);
  }, []);

  const handleLogin = (token: string) => {
    setStoredToken(token);
    setAuthenticated(true);
  };

  const handleLogout = () => {
    clearStoredToken();
    setAuthenticated(false);
  };

  if (!authenticated) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <BrowserRouter>
      <AppShell onLogout={handleLogout}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
