import { isDemoMode } from '../demo/demoApi';

export function DemoBanner() {
  if (!isDemoMode()) return null;

  return (
    <div className="bg-amber-500 text-white text-center py-2 px-4 text-sm font-medium sticky top-0 z-50">
      <span className="inline-flex items-center gap-2">
        <span className="px-1.5 py-0.5 bg-white text-amber-600 rounded text-xs font-bold uppercase tracking-wide">Demo</span>
        You are viewing a demo with sample data. No real patient information is used.
        <a href="https://github.com/matthewhmaxwell/trialibre" target="_blank" rel="noopener"
          className="underline font-semibold hover:text-amber-100 ml-1">
          Install Trialibre
        </a>
      </span>
    </div>
  );
}
