import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

interface TrialSummary {
  nct_id: string;
  brief_title: string;
  phase: string | null;
  status: string | null;
  diseases: string[];
  sponsor: string | null;
  enrollment: number | null;
}

export function TrialsPage() {
  const { t } = useTranslation();
  const [trials, setTrials] = useState<TrialSummary[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/trials')
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => { setTrials(data.trials || []); setLoading(false); })
      .catch(() => { setTrials([]); setLoading(false); });
  }, []);

  const filtered = trials.filter(tr =>
    tr.brief_title.toLowerCase().includes(search.toLowerCase()) ||
    tr.nct_id.toLowerCase().includes(search.toLowerCase()) ||
    tr.diseases.some(d => d.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-900">{t('nav.trials')}</h1>
        <span className="text-sm text-gray-500">{trials.length} trials loaded</span>
      </div>

      <input type="text" value={search} onChange={e => setSearch(e.target.value)}
        placeholder="Search trials by name, NCT ID, or disease..."
        className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm mb-4" />

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="bg-gray-100 animate-pulse rounded-lg h-20" />
          ))}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg divide-y">
          {filtered.length === 0 ? (
            <p className="p-4 text-sm text-gray-500">No trials found</p>
          ) : (
            filtered.slice(0, 50).map(trial => (
              <div key={trial.nct_id} className="p-3 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 leading-snug">{trial.brief_title}</p>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                      <span>{trial.nct_id}</span>
                      {trial.phase && <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">{trial.phase}</span>}
                      {trial.status && <span className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">{trial.status}</span>}
                    </div>
                  </div>
                  {trial.enrollment && (
                    <span className="text-xs text-gray-500 shrink-0 ml-3">{trial.enrollment} enrolled</span>
                  )}
                </div>
                {trial.diseases.length > 0 && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {trial.diseases.slice(0, 3).map(d => (
                      <span key={d} className="px-1.5 py-0.5 bg-green-50 text-green-700 text-xs rounded">{d}</span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
          {filtered.length > 50 && (
            <p className="p-3 text-xs text-gray-500 text-center">Showing 50 of {filtered.length} results</p>
          )}
        </div>
      )}
    </div>
  );
}
