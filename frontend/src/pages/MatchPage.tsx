import { useTranslation } from 'react-i18next';
import { PatientInput } from '../components/PatientInput';
import { MatchProgress } from '../components/MatchProgress';
import { TrialCard } from '../components/TrialCard';
import { FilterBar } from '../components/FilterBar';
import { Explainer } from '../components/Explainer';
import { useMatch } from '../hooks/useMatch';

export function MatchPage() {
  const { t } = useTranslation();
  const { result, phase, error, filter, setFilter, runMatch, reset } = useMatch();

  const filteredTrials = result?.rankings.filter(r => filter === 'all' || r.strength === filter) ?? [];

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Input phase */}
      {(phase === 'idle' || phase === 'error') && (
        <>
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{t('wizard.welcome_title')}</h1>
            <p className="text-gray-500 text-sm max-w-lg mx-auto">{t('wizard.welcome_subtitle')}</p>
          </div>
          <PatientInput onSubmit={text => runMatch(text)} disabled={false} />
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}
          <div className="mt-6 text-center">
            <Explainer />
          </div>
        </>
      )}

      {/* Progress phase */}
      {(phase === 'searching' || phase === 'checking' || phase === 'ranking' || phase === 'reading') && (
        <MatchProgress phase={phase} />
      )}

      {/* Results phase */}
      {phase === 'done' && result && (
        <>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-gray-700">
                {t('match.found_summary', { count: result.strong_count + result.possible_count, total: result.total_trials_screened })}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {result.retrieval_time_ms + result.matching_time_ms + result.ranking_time_ms}ms total
                {result.sandbox_mode && ' · sandbox data'}
              </p>
            </div>
            <button onClick={reset}
              className="px-3 py-1.5 text-xs text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50">
              New Search
            </button>
          </div>

          <FilterBar filter={filter} setFilter={setFilter} result={result} />

          <div className="mt-4">
            {filteredTrials.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p className="font-medium">{t('match.no_results')}</p>
                <p className="text-sm mt-1">{t('match.no_results_tips')}</p>
              </div>
            ) : (
              filteredTrials.map(trial => (
                <TrialCard key={trial.trial_id} trial={trial} />
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
