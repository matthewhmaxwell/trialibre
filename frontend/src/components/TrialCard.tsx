import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { CriterionResult, TrialScore } from '../types/api';

const strengthStyles = {
  strong: { bg: 'bg-green-50 border-green-200', badge: 'bg-green-100 text-green-800', icon: '●' },
  possible: { bg: 'bg-yellow-50 border-yellow-200', badge: 'bg-yellow-100 text-yellow-800', icon: '◐' },
  unlikely: { bg: 'bg-gray-50 border-gray-200', badge: 'bg-gray-100 text-gray-600', icon: '○' },
};

// Visual treatment for each per-criterion verdict. Greens = patient meets
// the inclusion / clears the exclusion. Reds = blocks enrollment. Amber =
// model couldn't tell. Mirrors the badge styling at the top of the card
// so the expanded view feels continuous with the summary.
const labelStyles: Record<string, { badge: string; icon: string; label: string }> = {
  included: { badge: 'bg-green-100 text-green-800', icon: '✓', label: 'Met' },
  'not included': { badge: 'bg-red-100 text-red-800', icon: '✗', label: 'Not met' },
  excluded: { badge: 'bg-red-100 text-red-800', icon: '✗', label: 'Excluded' },
  'not excluded': { badge: 'bg-green-100 text-green-800', icon: '✓', label: 'Cleared' },
  'not applicable': { badge: 'bg-gray-100 text-gray-600', icon: '—', label: 'N/A' },
  'not enough information': { badge: 'bg-amber-100 text-amber-800', icon: '?', label: 'Unknown' },
};

function CriterionRow({ result }: { result: CriterionResult }) {
  const style = labelStyles[result.label] || labelStyles['not enough information'];
  const reasoning = result.plain_reasoning || result.reasoning;
  return (
    <li className="border-l-2 border-gray-200 pl-3 py-2">
      <div className="flex items-start gap-2">
        <span className={`inline-flex items-center justify-center shrink-0 w-5 h-5 rounded-full text-[10px] font-bold ${style.badge}`}
              title={style.label} aria-label={style.label}>
          {style.icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-900 leading-snug">{result.criterion_text}</p>
          {reasoning && (
            <p className="text-xs text-gray-600 mt-1 leading-snug">{reasoning}</p>
          )}
          {result.evidence_sentence_ids.length > 0 && (
            <div className="mt-1 flex flex-wrap items-center gap-1 text-[10px] text-gray-500">
              <span>Evidence:</span>
              {result.evidence_sentence_ids.map((id) => (
                <span key={id} className="px-1.5 py-0.5 bg-gray-100 rounded font-mono">
                  s{id}
                </span>
              ))}
              <span className="text-gray-400">— from patient note</span>
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

export function TrialCard({ trial, onRefer }: { trial: TrialScore; onRefer?: (t: TrialScore) => void }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const s = strengthStyles[trial.strength];
  const pct = Math.round(trial.combined_score * 100);

  return (
    <div className={`border rounded-lg p-4 mb-3 transition-all ${s.bg}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${s.badge}`}>
              {s.icon} {t(`match.${trial.strength}`)}
            </span>
            <span className="text-xs text-gray-500">{pct}% match</span>
          </div>
          <h3 className="font-medium text-gray-900 text-sm leading-snug">{trial.trial_title}</h3>
          <p className="text-xs text-gray-500 mt-1">{trial.trial_id}</p>
        </div>

        <div className="flex flex-col items-end gap-1 shrink-0">
          <div className="w-12 h-12 relative">
            <svg viewBox="0 0 36 36" className="w-12 h-12 -rotate-90">
              <circle cx="18" cy="18" r="16" fill="none" stroke="#e5e7eb" strokeWidth="3" />
              <circle cx="18" cy="18" r="16" fill="none" stroke={trial.strength === 'strong' ? '#22c55e' : trial.strength === 'possible' ? '#eab308' : '#9ca3af'}
                strokeWidth="3" strokeDasharray={`${pct} ${100 - pct}`} strokeLinecap="round" />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-gray-700">{pct}</span>
          </div>
        </div>
      </div>

      {/* Criteria summary bar */}
      <div className="flex items-center gap-3 mt-3 text-xs">
        <span className="text-green-700">{trial.criteria_met} {t('match.criteria_met')}</span>
        <span className="text-red-600">{trial.criteria_not_met} {t('match.criteria_not_met')}</span>
        <span className="text-amber-600">{trial.criteria_unknown} {t('match.criteria_unknown')}</span>
        {trial.nearest_site_name && (
          <span className="text-gray-500 ml-auto">
            {trial.nearest_site_name}
            {trial.nearest_site_distance_km != null && ` · ${Math.round(trial.nearest_site_distance_km)} km`}
          </span>
        )}
      </div>

      {/* Drug interactions */}
      {trial.drug_interaction_flags.length > 0 && (
        <div className="mt-2 px-2 py-1 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          ⚠ Drug interactions: {trial.drug_interaction_flags.join(', ')}
        </div>
      )}

      {/* Expandable details */}
      <button onClick={() => setExpanded(!expanded)}
        className="mt-2 text-xs text-blue-600 hover:text-blue-800 font-medium">
        {expanded ? 'Hide details' : t('match.view_details')}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 text-sm">
          <div>
            <h4 className="font-medium text-gray-700 text-xs uppercase tracking-wide mb-1">Relevance</h4>
            <p className="text-gray-600 text-sm">{trial.relevance_explanation}</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-700 text-xs uppercase tracking-wide mb-1">Eligibility</h4>
            <p className="text-gray-600 text-sm">{trial.eligibility_explanation}</p>
          </div>

          {/* Per-criterion breakdown — the actual "criterion-level
              explainability" the README promises. Renders only when the
              backend supplied the per-criterion data (recent backends
              do; older saved results and demo-mode fixtures may not). */}
          {(trial.inclusion_results ?? []).length > 0 && (
            <div>
              <h4 className="font-medium text-gray-700 text-xs uppercase tracking-wide mb-1">
                Inclusion criteria ({trial.inclusion_results!.length})
              </h4>
              <ul className="space-y-0">
                {trial.inclusion_results!.map((r) => (
                  <CriterionRow key={`inc-${r.criterion_index}`} result={r} />
                ))}
              </ul>
            </div>
          )}
          {(trial.exclusion_results ?? []).length > 0 && (
            <div>
              <h4 className="font-medium text-gray-700 text-xs uppercase tracking-wide mb-1">
                Exclusion criteria ({trial.exclusion_results!.length})
              </h4>
              <ul className="space-y-0">
                {trial.exclusion_results!.map((r) => (
                  <CriterionRow key={`exc-${r.criterion_index}`} result={r} />
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            {onRefer && (
              <button onClick={() => onRefer(trial)}
                className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700">
                {t('match.refer')}
              </button>
            )}
            <button onClick={() => window.print()}
              className="px-3 py-1.5 bg-gray-100 text-gray-700 text-xs rounded-lg hover:bg-gray-200">
              {t('match.print')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
