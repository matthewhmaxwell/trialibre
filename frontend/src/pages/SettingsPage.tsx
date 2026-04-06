import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

interface SettingsData {
  llm_provider: string;
  api_key: string;
  model: string;
  base_url: string;
  sandbox_mode: boolean;
  privacy: {
    deid_enabled: boolean;
    delete_after_match: boolean;
    keep_audit_log: boolean;
    allow_local_storage: boolean;
  };
  referrals: {
    default_email: string;
    cc_email: string;
    whatsapp_number: string;
    include_patient_summary: boolean;
    include_criteria_details: boolean;
    custom_message: string;
  };
}

export function SettingsPage() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const defaults: SettingsData = {
      llm_provider: 'ollama', api_key: '', model: 'llama3.1', base_url: 'http://localhost:11434',
      sandbox_mode: true,
      privacy: { deid_enabled: true, delete_after_match: true, keep_audit_log: false, allow_local_storage: false },
      referrals: { default_email: '', cc_email: '', whatsapp_number: '', include_patient_summary: true, include_criteria_details: true, custom_message: '' },
    };
    fetch('/api/v1/settings')
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => setSettings({ ...defaults, ...data }))
      .catch(() => setSettings(defaults));
  }, []);

  const save = async () => {
    if (!settings) return;
    setSaved(false);
    setError('');
    try {
      const resp = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!resp.ok) throw new Error('Save failed');
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError('Failed to save settings');
    }
  };

  if (!settings) return <div className="p-8 text-center text-gray-500">Loading...</div>;

  const update = (path: string, value: unknown) => {
    setSettings(prev => {
      if (!prev) return prev;
      const copy = structuredClone(prev);
      const keys = path.split('.');
      let obj: Record<string, unknown> = copy as unknown as Record<string, unknown>;
      for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]] as Record<string, unknown>;
      obj[keys[keys.length - 1]] = value;
      return copy;
    });
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <h1 className="text-xl font-bold text-gray-900 mb-6">{t('nav.settings')}</h1>

      {/* LLM Provider */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">AI Service</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Provider</label>
            <select value={settings.llm_provider} onChange={e => update('llm_provider', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="openai">OpenAI</option>
              <option value="ollama">Ollama (Local)</option>
              <option value="openai_compat">OpenAI-Compatible</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">API Key</label>
            <input type="password" value={settings.api_key} onChange={e => update('api_key', e.target.value)}
              placeholder="sk-..." className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Model</label>
            <input type="text" value={settings.model} onChange={e => update('model', e.target.value)}
              placeholder="claude-sonnet-4-20250514" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          {(settings.llm_provider === 'ollama' || settings.llm_provider === 'openai_compat') && (
            <div>
              <label className="block text-sm text-gray-600 mb-1">Base URL</label>
              <input type="text" value={settings.base_url} onChange={e => update('base_url', e.target.value)}
                placeholder="http://localhost:11434" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
          )}
        </div>
      </section>

      {/* Privacy */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Privacy</h2>
        <div className="space-y-3">
          {[
            { path: 'privacy.deid_enabled', label: 'De-identify patient data before sending to AI' },
            { path: 'privacy.delete_after_match', label: t('wizard.delete_after') },
            { path: 'privacy.keep_audit_log', label: t('wizard.keep_logs') },
            { path: 'privacy.allow_local_storage', label: t('wizard.allow_storage') },
          ].map(item => (
            <label key={item.path} className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox"
                checked={(item.path.split('.').reduce((o: unknown, k) => (o as Record<string, unknown>)[k], settings)) as boolean}
                onChange={e => update(item.path, e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600" />
              <span className="text-sm text-gray-700">{item.label}</span>
            </label>
          ))}
        </div>
      </section>

      {/* Referrals */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Referrals</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Default referral email</label>
            <input type="email" value={settings.referrals.default_email}
              onChange={e => update('referrals.default_email', e.target.value)}
              placeholder="crc@hospital.org" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">CC email (optional)</label>
            <input type="email" value={settings.referrals.cc_email}
              onChange={e => update('referrals.cc_email', e.target.value)}
              placeholder="pi@hospital.org" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">WhatsApp number (optional)</label>
            <input type="tel" value={settings.referrals.whatsapp_number}
              onChange={e => update('referrals.whatsapp_number', e.target.value)}
              placeholder="+55 11 99999-9999" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={settings.referrals.include_patient_summary}
              onChange={e => update('referrals.include_patient_summary', e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600" />
            <span className="text-sm text-gray-700">Include patient summary in referral</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={settings.referrals.include_criteria_details}
              onChange={e => update('referrals.include_criteria_details', e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600" />
            <span className="text-sm text-gray-700">Include criteria match details</span>
          </label>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Custom message template (optional)</label>
            <textarea value={settings.referrals.custom_message}
              onChange={e => update('referrals.custom_message', e.target.value)}
              placeholder="Dear coordinator, I would like to refer a patient for the following trial..."
              rows={3} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
        </div>
      </section>

      {/* Sandbox */}
      <section className="mb-8">
        <label className="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" checked={settings.sandbox_mode}
            onChange={e => update('sandbox_mode', e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600" />
          <span className="text-sm text-gray-700">Sandbox mode (use sample data)</span>
        </label>
      </section>

      {/* Save */}
      <div className="flex items-center gap-3">
        <button onClick={save}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          Save Settings
        </button>
        {saved && <span className="text-sm text-green-600">Saved</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </div>
  );
}
