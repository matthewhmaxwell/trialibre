import { HashRouter, BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { isDemoMode } from './demo/demoApi';
import { useTranslation } from 'react-i18next';
import { MatchPage } from './pages/MatchPage';
import { BatchPage } from './pages/BatchPage';
import { DashboardPage } from './pages/DashboardPage';
import { TrialsPage } from './pages/TrialsPage';
import { SettingsPage } from './pages/SettingsPage';
import { SandboxBanner } from './components/SandboxBanner';
import { DemoBanner } from './components/DemoBanner';
import { PrivacyIndicator } from './components/PrivacyIndicator';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { useSettings } from './hooks/useSettings';
import './i18n';

function Layout({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const { health, privacy } = useSettings();

  const navItems = [
    { to: '/', label: t('nav.match'), icon: '🔍' },
    { to: '/batch', label: t('nav.batch'), icon: '📋' },
    { to: '/dashboard', label: t('nav.dashboard'), icon: '📊' },
    { to: '/trials', label: t('nav.trials'), icon: '🧪' },
    { to: '/settings', label: t('nav.settings'), icon: '⚙️' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <DemoBanner />
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <h1 className="text-lg font-bold text-gray-900">Trialibre</h1>
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map(item => (
                <NavLink key={item.to} to={item.to} end
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                    ${isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            {health && (
              <span className={`w-2 h-2 rounded-full ${health.llm_connected ? 'bg-green-500' : 'bg-red-400'}`}
                title={health.llm_connected ? `${health.llm_provider} connected` : 'No AI connected'} />
            )}
          </div>
        </div>
      </header>

      <SandboxBanner visible={health?.sandbox_mode ?? false} />

      {/* Main content */}
      <main className="pb-24 md:pb-16">
        {children}
      </main>

      {/* Footer */}
      <footer className="hidden md:block border-t border-gray-200 py-4 text-center text-xs text-gray-400">
        {t('app.name')} &middot; {t('app.org')} &middot; Non-Profit &middot; Open Source
      </footer>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40">
        <div className="flex items-center justify-around h-14">
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} end
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 text-xs
                ${isActive ? 'text-blue-600' : 'text-gray-500'}`}>
              <span className="text-base">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>

      <PrivacyIndicator status={privacy} />
    </div>
  );
}

export default function App() {
  // Use HashRouter for static hosting (demo mode), BrowserRouter for backend mode
  const Router = isDemoMode() ? HashRouter : BrowserRouter;

  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<MatchPage />} />
          <Route path="/batch" element={<BatchPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/trials" element={<TrialsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}
