import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export function Explainer() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <button onClick={() => setOpen(true)}
        className="text-xs text-blue-600 hover:text-blue-800 underline">
        {t('explainer.title')}
      </button>
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-900">
      <h4 className="font-medium mb-2">{t('explainer.title')}</h4>
      <p className="text-blue-800 leading-relaxed">{t('explainer.body')}</p>
      <button onClick={() => setOpen(false)}
        className="mt-3 px-3 py-1 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700">
        {t('explainer.got_it')}
      </button>
    </div>
  );
}
