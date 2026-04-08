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
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <DemoBanner />

      {/* AIMR Standard Header */}
      <header style={{position:'sticky',top:0,zIndex:100,background:'rgba(255,255,255,0.97)',backdropFilter:'blur(8px)',borderBottom:'1px solid #e5e7eb'}}>
        <div style={{maxWidth:1100,margin:'0 auto',padding:'0 1.5rem',display:'flex',alignItems:'center',justifyContent:'space-between',height:72}}>
          <a href="https://aimronline.org" style={{textDecoration:'none'}}>
            <img src="https://aimronline.org/aimr-logo.png" alt="AIM Research" style={{height:36}} />
          </a>
          <nav style={{display:'flex',gap:'2rem',alignItems:'center'}}>
            <a href="https://aimronline.org/about.html" style={{fontFamily:'Inter,sans-serif',fontSize:'0.9rem',fontWeight:500,color:'#4b5563',textDecoration:'none'}}>About</a>
            <a href="https://aimronline.org/tools.html" style={{fontFamily:'Inter,sans-serif',fontSize:'0.9rem',fontWeight:500,color:'#4b5563',textDecoration:'none'}}>Tools</a>
            <a href="https://aimronline.org/notes.html" style={{fontFamily:'Inter,sans-serif',fontSize:'0.9rem',fontWeight:500,color:'#4b5563',textDecoration:'none'}}>Notes</a>
          </nav>
        </div>
      </header>

      {/* App navigation bar (below AIMR header) */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 h-12 flex items-center justify-between">
          <div className="flex items-center gap-5">
            <span className="text-base font-bold text-gray-900">Trialibre</span>
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
      </div>

      <SandboxBanner visible={health?.sandbox_mode ?? false} />

      {/* Main content */}
      <main className="flex-1 pb-24 md:pb-16">
        {children}
      </main>

      {/* AIMR Standard Footer */}
      <footer style={{background:'#0f0a1e',color:'rgba(255,255,255,0.6)',padding:'2.5rem 0',fontSize:'0.85rem',fontFamily:'Inter,sans-serif'}}>
        <div style={{maxWidth:1100,margin:'0 auto',padding:'0 1.5rem',display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:'1rem'}}>
          <span>&copy; 2026 American Institute for Medical Research, LLC</span>
          <div style={{display:'flex',gap:'1.5rem'}}>
            <a href="https://www.linkedin.com/company/aimronline" target="_blank" rel="noopener" style={{color:'rgba(255,255,255,0.6)',textDecoration:'none'}}>LinkedIn</a>
            <a href="https://aimronline.org/about.html#privacy" style={{color:'rgba(255,255,255,0.6)',textDecoration:'none'}}>Privacy</a>
          </div>
        </div>
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
