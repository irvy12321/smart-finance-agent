import { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import TopNavBar from './TopNavBar'
import StatusBar from './StatusBar'

interface MainLayoutProps {
  children: ReactNode
  showStatusBar?: boolean
}

export default function MainLayout({ children, showStatusBar = true }: MainLayoutProps) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col h-screen bg-dark-bg">
      <TopNavBar />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
      <div className="px-4 py-1.5 text-xs text-center text-gray-400 bg-dark-bg border-t border-gray-700/60">
        {t('common.disclaimer')}
      </div>
      {showStatusBar && <StatusBar />}
    </div>
  )
}
