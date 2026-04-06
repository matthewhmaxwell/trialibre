import { useTranslation } from 'react-i18next';

const languages = [
  { code: 'en', label: 'EN' },
  { code: 'fr', label: 'FR' },
  { code: 'pt', label: 'PT' },
  { code: 'es', label: 'ES' },
  { code: 'ar', label: 'AR' },
];

export function LanguageSwitcher() {
  const { i18n } = useTranslation();

  return (
    <select value={i18n.language} onChange={e => i18n.changeLanguage(e.target.value)}
      className="text-xs bg-transparent border border-gray-300 rounded px-2 py-1 text-gray-600">
      {languages.map(l => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  );
}
