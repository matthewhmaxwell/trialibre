/**
 * Vitest setup: extends `expect` with testing-library matchers and stubs
 * the i18next initialization so components that call `useTranslation()`
 * just echo their key (predictable assertions, no async i18n boot).
 */

import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Synchronous, fixture-only init. Real strings come from src/i18n/en.json
// in production; tests treat translations as stable identifiers so a
// wording tweak doesn't cascade through every snapshot.
i18n.use(initReactI18next).init({
  lng: 'en',
  fallbackLng: 'en',
  resources: { en: { translation: {} } },
  interpolation: { escapeValue: false },
  // Return the key as-is when missing — tests assert against keys, not
  // localized strings, so we get stable text regardless of locale state.
  parseMissingKeyHandler: (key: string) => key,
});

afterEach(() => {
  cleanup();
});
