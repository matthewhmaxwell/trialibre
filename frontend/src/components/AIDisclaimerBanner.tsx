import { useState } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * Decision-support / AI-disclaimer banner shown above match results.
 *
 * Why this exists: the matching pipeline is LLM-driven. On the validated
 * Sonnet configuration, the 24-pair sandbox eval scored 79% strict
 * accuracy with no gross errors — but defensible misses still happen,
 * and small local models (e.g. Ollama llama3.2:3b) hallucinate facts
 * outright (the canonical example in our internal eval was a confident
 * "amlodipine is an SGLT2 inhibitor" claim). Anyone using this UI to
 * inform a real clinical decision needs to see, every time, that
 * results are decision-support output and not eligibility
 * determinations.
 *
 * Dismissible per-session (sessionStorage) so power users aren't fatigued
 * across many searches in one sitting, but it returns on a fresh tab so
 * the warning is never permanently hidden.
 */
const STORAGE_KEY = 'trialibre.ai_disclaimer.dismissed';

export function AIDisclaimerBanner() {
  const { t } = useTranslation();
  const [dismissed, setDismissed] = useState<boolean>(() => {
    try {
      return sessionStorage.getItem(STORAGE_KEY) === '1';
    } catch {
      return false;
    }
  });

  if (dismissed) return null;

  const dismiss = () => {
    try {
      sessionStorage.setItem(STORAGE_KEY, '1');
    } catch {
      // sessionStorage can throw in some embedded contexts; degrade silently.
    }
    setDismissed(true);
  };

  return (
    <div
      role="alert"
      className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-amber-900"
    >
      <div className="flex items-start gap-2">
        <span aria-hidden="true" className="mt-0.5 text-base leading-none">⚠</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium">{t('match.ai_disclaimer_banner_title')}</p>
          <p className="mt-1 text-xs leading-snug">{t('match.ai_disclaimer_banner_body')}</p>
        </div>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss"
          className="shrink-0 rounded p-1 text-amber-700 hover:bg-amber-100"
        >
          ×
        </button>
      </div>
    </div>
  );
}
