import { useState, useCallback } from 'react';
import type { MatchResponse, MatchFilter } from '../types/api';

type MatchPhase = 'idle' | 'reading' | 'searching' | 'checking' | 'ranking' | 'done' | 'error';

interface UseMatchReturn {
  result: MatchResponse | null;
  phase: MatchPhase;
  progress: { completed: number; total: number };
  error: string | null;
  filter: MatchFilter;
  setFilter: (f: MatchFilter) => void;
  runMatch: (patientText: string, maxTrials?: number) => Promise<void>;
  reset: () => void;
}

export function useMatch(): UseMatchReturn {
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [phase, setPhase] = useState<MatchPhase>('idle');
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<MatchFilter>('all');

  const runMatch = useCallback(async (patientText: string, maxTrials = 50) => {
    setPhase('searching');
    setError(null);
    setResult(null);
    setProgress({ completed: 0, total: 0 });

    try {
      setPhase('checking');
      const resp = await fetch('/api/v1/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patient_text: patientText, max_trials: maxTrials }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }

      setPhase('ranking');
      const data: MatchResponse = await resp.json();
      setResult(data);
      setPhase('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Matching failed');
      setPhase('error');
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setPhase('idle');
    setError(null);
    setFilter('all');
  }, []);

  return { result, phase, progress, error, filter, setFilter, runMatch, reset };
}
