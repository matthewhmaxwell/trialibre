import { useTranslation } from 'react-i18next';
import type { MatchFilter, MatchResponse } from '../types/api';

interface Props {
  filter: MatchFilter;
  setFilter: (f: MatchFilter) => void;
  result: MatchResponse;
}

const filters: { key: MatchFilter; color: string }[] = [
  { key: 'all', color: 'bg-gray-100 text-gray-700' },
  { key: 'strong', color: 'bg-green-100 text-green-700' },
  { key: 'possible', color: 'bg-yellow-100 text-yellow-700' },
  { key: 'unlikely', color: 'bg-gray-100 text-gray-500' },
];

export function FilterBar({ filter, setFilter, result }: Props) {
  const { t } = useTranslation();

  const counts: Record<MatchFilter, number> = {
    all: result.rankings.length,
    strong: result.strong_count,
    possible: result.possible_count,
    unlikely: result.unlikely_count,
  };

  return (
    <div className="flex gap-2 flex-wrap">
      {filters.map(f => (
        <button key={f.key} onClick={() => setFilter(f.key)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all
            ${filter === f.key ? f.color + ' ring-2 ring-offset-1 ring-blue-400' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}>
          {f.key === 'all' ? 'All' : t(`match.${f.key}`)} ({counts[f.key]})
        </button>
      ))}
    </div>
  );
}
