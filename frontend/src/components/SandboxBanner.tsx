import { useTranslation } from 'react-i18next';

export function SandboxBanner({ visible }: { visible: boolean }) {
  const { t } = useTranslation();
  if (!visible) return null;

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-center text-sm text-amber-800">
      <span className="font-medium">Sandbox Mode</span> — {t('sandbox.banner')}
    </div>
  );
}
