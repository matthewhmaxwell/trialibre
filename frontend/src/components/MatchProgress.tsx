import { useTranslation } from 'react-i18next';

type Phase = 'idle' | 'reading' | 'searching' | 'checking' | 'ranking' | 'done' | 'error';

const steps: { phase: Phase; key: string }[] = [
  { phase: 'searching', key: 'match.searching' },
  { phase: 'checking', key: 'match.checking' },
  { phase: 'ranking', key: 'match.ranking' },
];

export function MatchProgress({ phase }: { phase: Phase }) {
  const { t } = useTranslation();
  if (phase === 'idle' || phase === 'done' || phase === 'error') return null;

  const currentIdx = steps.findIndex(s => s.phase === phase);

  return (
    <div className="w-full max-w-md mx-auto py-8">
      <div className="flex items-center justify-between mb-6">
        {steps.map((step, i) => (
          <div key={step.phase} className="flex items-center flex-1">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all
              ${i < currentIdx ? 'bg-green-500 text-white' : i === currentIdx ? 'bg-blue-500 text-white animate-pulse' : 'bg-gray-200 text-gray-500'}`}>
              {i < currentIdx ? '✓' : i + 1}
            </div>
            {i < steps.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 ${i < currentIdx ? 'bg-green-500' : 'bg-gray-200'}`} />
            )}
          </div>
        ))}
      </div>
      <p className="text-center text-gray-600 text-sm">{t(steps[currentIdx]?.key || 'match.searching')}</p>
    </div>
  );
}
