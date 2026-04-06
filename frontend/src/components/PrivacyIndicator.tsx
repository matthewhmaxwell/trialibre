import { useTranslation } from 'react-i18next';
import type { PrivacyStatus } from '../types/api';

const colorMap = {
  green: 'bg-green-100 text-green-800 border-green-300',
  blue: 'bg-blue-100 text-blue-800 border-blue-300',
  yellow: 'bg-yellow-100 text-yellow-800 border-yellow-300',
};

export function PrivacyIndicator({ status }: { status: PrivacyStatus | null }) {
  const { t } = useTranslation();
  if (!status || !status.color || !status.label) return null;

  const classes = colorMap[status.color] || colorMap.green;
  const details = Array.isArray(status.details) ? status.details.join('\n') : '';

  return (
    <div className={`fixed bottom-4 left-4 z-50 flex items-center gap-2 px-3 py-2 rounded-full border text-sm font-medium cursor-pointer ${classes}`}
         title={details}>
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
      </svg>
      {t(`privacy.${status.label.toLowerCase()}`)}
    </div>
  );
}
