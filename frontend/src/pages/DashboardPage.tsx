import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

interface DashboardData {
  total_matches: number;
  total_referrals: number;
  avg_match_score: number;
  top_trials: { trial_id: string; title: string; match_count: number }[];
  recent_matches: { patient_id: string; timestamp: string; strong: number; possible: number }[];
  ta_distribution: Record<string, number>;
}

interface FeedbackAggregate {
  total: number;
  counts: { correct: number; incorrect: number; unsure: number };
  agreement_rate: number | null;
}

export function DashboardPage() {
  const { t } = useTranslation();
  const [data, setData] = useState<DashboardData | null>(null);
  const [feedback, setFeedback] = useState<FeedbackAggregate | null>(null);

  useEffect(() => {
    fetch('/api/v1/dashboard/summary')
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch(e => {
        console.warn('Dashboard fetch failed:', e.message);
        setData({
          total_matches: 0, total_referrals: 0, avg_match_score: 0,
          top_trials: [], recent_matches: [], ta_distribution: {},
        });
      });

    // Surface coordinator feedback aggregate next to match metrics so
    // operators can see at a glance how often clinicians have agreed
    // with the model's verdicts. Empty state is fine; the card just
    // says "no feedback yet."
    fetch('/api/v1/feedback/aggregate')
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setFeedback)
      .catch(() => setFeedback({ total: 0, counts: { correct: 0, incorrect: 0, unsure: 0 }, agreement_rate: null }));
  }, []);

  if (!data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="text-xl font-bold text-gray-900 mb-6">{t('nav.dashboard')}</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-gray-100 animate-pulse rounded-lg h-24" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-xl font-bold text-gray-900 mb-6">{t('nav.dashboard')}</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Matches</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{data.total_matches}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Referrals Sent</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{data.total_referrals}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Avg Match Score</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{Math.round(data.avg_match_score * 100)}%</p>
        </div>
        {/* Coordinator agreement card — nullable when no feedback yet,
            otherwise shows the share of match cards a clinician marked
            "correct" out of the total verdicts. The single most useful
            number to track during a clinical pilot. */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Coordinator agreement</p>
          {feedback && feedback.total > 0 && feedback.agreement_rate !== null ? (
            <>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {Math.round(feedback.agreement_rate * 100)}%
              </p>
              <p className="text-[10px] text-gray-500 mt-0.5">
                {feedback.counts.correct} ✓ · {feedback.counts.incorrect} ✗ · {feedback.counts.unsure} ?
                <span className="text-gray-400"> ({feedback.total} verdicts)</span>
              </p>
            </>
          ) : (
            <p className="text-sm text-gray-500 mt-1 italic">No feedback yet</p>
          )}
        </div>
      </div>

      {/* Top trials */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Most Matched Trials</h2>
        <div className="bg-white border border-gray-200 rounded-lg divide-y">
          {data.top_trials.length === 0 ? (
            <p className="p-4 text-sm text-gray-500">No matches yet</p>
          ) : (
            data.top_trials.map(trial => (
              <div key={trial.trial_id} className="flex items-center justify-between p-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{trial.title}</p>
                  <p className="text-xs text-gray-500">{trial.trial_id}</p>
                </div>
                <span className="text-sm font-medium text-blue-600">{trial.match_count} matches</span>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Recent matches */}
      <section>
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Recent Activity</h2>
        <div className="bg-white border border-gray-200 rounded-lg divide-y">
          {data.recent_matches.length === 0 ? (
            <p className="p-4 text-sm text-gray-500">No recent activity</p>
          ) : (
            data.recent_matches.map((m, i) => (
              <div key={i} className="flex items-center justify-between p-3">
                <div>
                  <p className="text-sm text-gray-900">Patient {m.patient_id}</p>
                  <p className="text-xs text-gray-500">{new Date(m.timestamp).toLocaleString()}</p>
                </div>
                <div className="flex gap-2 text-xs">
                  <span className="text-green-700">{m.strong} strong</span>
                  <span className="text-yellow-700">{m.possible} possible</span>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
