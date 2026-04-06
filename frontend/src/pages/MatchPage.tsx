import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PatientInput } from '../components/PatientInput';
import { MatchProgress } from '../components/MatchProgress';
import { TrialCard } from '../components/TrialCard';
import { FilterBar } from '../components/FilterBar';
import { Explainer } from '../components/Explainer';
import { TrialUpload } from '../components/TrialUpload';
import { useMatch } from '../hooks/useMatch';

interface UploadedTrial {
  nct_id: string;
  brief_title: string;
  inclusion_count: number;
  exclusion_count: number;
}

export function MatchPage() {
  const { t } = useTranslation();
  const { result, phase, error, filter, setFilter, runMatch, reset } = useMatch();
  const [uploadedTrials, setUploadedTrials] = useState<UploadedTrial[]>([]);

  const filteredTrials = result?.rankings.filter(r => filter === 'all' || r.strength === filter) ?? [];

  const handleUpload = (res: UploadedTrial) => {
    setUploadedTrials(prev => [...prev.filter(t => t.nct_id !== res.nct_id), res]);
  };

  const removeUpload = (nctId: string) => {
    setUploadedTrials(prev => prev.filter(t => t.nct_id !== nctId));
  };

  const handleMatch = (text: string) => {
    const trialIds = uploadedTrials.length > 0 ? uploadedTrials.map(t => t.nct_id) : undefined;
    runMatch(text, 50, trialIds);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Input phase */}
      {(phase === 'idle' || phase === 'error') && (
        <>
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{t('wizard.welcome_title')}</h1>
            <p className="text-gray-500 text-sm max-w-lg mx-auto">{t('wizard.welcome_subtitle')}</p>
          </div>

          {/* Protocol upload */}
          <div className="mb-4">
            <TrialUpload onUpload={handleUpload} />
          </div>

          {/* Uploaded trial chips */}
          {uploadedTrials.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-2">
              <span className="text-xs text-gray-500 py-1">Matching against:</span>
              {uploadedTrials.map(t => (
                <span key={t.nct_id} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                  {t.brief_title.length > 30 ? t.brief_title.slice(0, 30) + '...' : t.brief_title}
                  <span className="text-blue-500">({t.inclusion_count}+{t.exclusion_count})</span>
                  <button onClick={() => removeUpload(t.nct_id)} className="text-blue-400 hover:text-blue-700 ml-0.5">&times;</button>
                </span>
              ))}
            </div>
          )}

          <PatientInput onSubmit={handleMatch} disabled={false} />
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
