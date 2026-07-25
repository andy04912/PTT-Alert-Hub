import { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { api, clearStoredToken, getStoredToken, setStoredToken } from './api/client';
import { AppShell } from './components/AppShell';
import { LoadingState } from './components/Feedback';
import { PwaManager } from './components/PwaManager';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { MatchesPage } from './pages/MatchesPage';
import { PushPage } from './pages/PushPage';
import { RegisterPage } from './pages/RegisterPage';
import { RulesPage } from './pages/RulesPage';
import { RunsPage } from './pages/RunsPage';
import { SettingsPage } from './pages/SettingsPage';
import type { LoginResponse, User } from './types';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(getStoredToken()));

  useEffect(() => {
    const handleExpired = () => {
      setUser(null);
      setLoading(false);
    };
    window.addEventListener('auth-expired', handleExpired);

    const token = getStoredToken();
    if (token) {
      api
        .getMe()
        .then(setUser)
        .catch(() => setUser(null))
        .finally(() => setLoading(false));
    }

    return () => window.removeEventListener('auth-expired', handleExpired);
  }, []);

  const handleAuthenticated = (response: LoginResponse) => {
    setStoredToken(response.access_token);
    setUser(response.user);
    setLoading(false);
  };

  const handleLogout = () => {
    clearStoredToken();
    setUser(null);
  };

  if (loading) return <LoadingState />;

  return (
    <BrowserRouter>
      <PwaManager />
      {user ? (
        <AppShell user={user} onLogout={handleLogout}>
          <Routes>
            <Route path="/" element={<DashboardPage isAdmin={user.is_admin} />} />
            <Route path="/rules" element={<RulesPage />} />
            <Route path="/matches" element={<MatchesPage />} />
            <Route path="/push" element={<PushPage />} />
            {user.is_admin && <Route path="/runs" element={<RunsPage />} />}
            {user.is_admin && <Route path="/settings" element={<SettingsPage />} />}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      ) : (
        <Routes>
          <Route path="/login" element={<LoginPage onAuthenticated={handleAuthenticated} />} />
          <Route path="/register" element={<RegisterPage onAuthenticated={handleAuthenticated} />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      )}
    </BrowserRouter>
  );
}
