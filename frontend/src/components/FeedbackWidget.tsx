import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { TrialScore } from '../types/api';

/**
 * Inline feedback widget for a single trial match.
 *
 * Three buttons (right / wrong / unsure) + an optional note. POSTs to
 * /api/v1/feedback. The verdict, the model output that prompted it,
 * and the score at the time of the verdict are persisted so we can
 * later analyze drift across model upgrades or prompt changes.
 *
 * UX rationale: the widget appears in the expanded TrialCard view so
 * the clinician sees it after they've already read the criterion-level
 * reasoning. Submission is one click for the verdict; the note is
 * progressive — the textarea only appears if the user picked
 * "incorrect" or "unsure" since "correct" doesn't usually need a
 * comment. Submitted state shows a brief confirmation, no full-page
 * disruption.
 */

type Verdict = 'correct' | 'incorrect' | 'unsure';

const verdicts: Array<{ key: Verdict; label: string; styles: string }> = [
  { key: 'correct', label: 'Correct', styles: 'border-green-300 text-green-700 hover:bg-green-50' },
  { key: 'incorrect', label: 'Incorrect', styles: 'border-red-300 text-red-700 hover:bg-red-50' },
  { key: 'unsure', label: 'Unsure', styles: 'border-amber-300 text-amber-700 hover:bg-amber-50' },
];

interface Props {
  patientId: string;
  trial: TrialScore;
  apiBase?: string;  // defaults to /api/v1; override for tests
}

export function FeedbackWidget({ patientId, trial, apiBase = '/api/v1' }: Props) {
  const { t } = useTranslation();
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (chosen: Verdict, withNote: boolean) => {
    setSubmitting(true);
    setError(null);
    try {
      const resp = await fetch(`${apiBase}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          trial_id: trial.trial_id,
          feedback_type: chosen,
          notes: withNote ? notes : '',
          // Capture context at the moment of the verdict so this row
          // is self-contained for later drift analysis.
          data: {
            strength: trial.strength,
            combined_score: trial.combined_score,
            relevance_score: trial.relevance_score,
            eligibility_score: trial.eligibility_score,
            criteria_met: trial.criteria_met,
            criteria_not_met: trial.criteria_not_met,
            criteria_excluded: trial.criteria_excluded,
            criteria_unknown: trial.criteria_unknown,
          },
        }),
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || `${resp.status} ${resp.statusText}`);
      }
      setSubmitted(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="mt-2 text-xs text-gray-600 italic">
        ✓ {t('feedback.thanks')}
      </div>
    );
  }

  return (
    <div className="mt-3 border-t border-gray-200 pt-2 text-xs">
      <p className="text-gray-600 mb-1">{t('feedback.prompt')}</p>
      <div className="flex flex-wrap gap-2">
        {verdicts.map((v) => (
          <button
            key={v.key}
            type="button"
            disabled={submitting}
            onClick={() => {
              if (v.key === 'correct') {
                // Fast path: no note required.
                void submit('correct', false);
              } else {
                // Reveal the note field; submit happens on the explicit
                // Send button so the user can write before posting.
                setVerdict(v.key);
              }
            }}
            className={`px-2 py-1 rounded border transition-colors ${v.styles} ${
              verdict === v.key ? 'ring-2 ring-offset-1 ring-current' : ''
            } disabled:opacity-50`}
            aria-pressed={verdict === v.key}
          >
            {t(`feedback.${v.key}`, v.label)}
          </button>
        ))}
      </div>

      {(verdict === 'incorrect' || verdict === 'unsure') && (
        <div className="mt-2">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={t('feedback.notes_placeholder')}
            rows={2}
            disabled={submitting}
            className="w-full text-xs border border-gray-200 rounded p-1.5 focus:border-blue-300 focus:outline-none focus:ring-1 focus:ring-blue-200"
          />
          <button
            type="button"
            disabled={submitting}
            onClick={() => void submit(verdict, true)}
            className="mt-1 px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? t('feedback.sending') : t('feedback.send')}
          </button>
        </div>
      )}

      {error && (
        <p className="mt-1 text-red-600">{t('feedback.error')}: {error}</p>
      )}
    </div>
  );
}
