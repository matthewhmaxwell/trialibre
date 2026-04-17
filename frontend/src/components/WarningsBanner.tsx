import { useState } from 'react';

interface Props {
  warnings: string[];
}

/** Dismissible yellow banner that surfaces environment warnings from /health. */
export function WarningsBanner({ warnings }: Props) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const visible = warnings.filter(w => !dismissed.has(w));

  if (visible.length === 0) return null;

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm">
      <div className="max-w-5xl mx-auto">
        {visible.map((w, i) => (
          <div key={i} className="flex items-start gap-2 py-1">
            <span className="text-amber-600 mt-0.5" aria-hidden="true">⚠</span>
            <span className="flex-1 text-amber-900">{w}</span>
            <button
              onClick={() => setDismissed(prev => new Set([...prev, w]))}
              aria-label="Dismiss warning"
              className="text-amber-600 hover:text-amber-900 text-lg leading-none"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
