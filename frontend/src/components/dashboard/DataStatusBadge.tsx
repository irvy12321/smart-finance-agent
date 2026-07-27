import { FlaskConical } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function DataStatusBadge() {
  const { t } = useTranslation()

  return (
    <span
      className="inline-flex items-center gap-1 whitespace-nowrap rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-300"
      title={t('common.simulatedDataNotice')}
    >
      <FlaskConical className="h-3 w-3" />
      {t('common.simulatedData')}
    </span>
  )
}
