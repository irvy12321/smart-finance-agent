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
    <div className="flex h-screen min-h-0 flex-col overflow-hidden bg-dark-bg text-primary-200">
      <TopNavBar />
      <main className="app-main flex-1 min-h-0 overflow-auto">
        {children}
      </main>
      <div className="flex-shrink-0 px-6 py-1.5 text-center text-xs text-gray-400 bg-dark-bg border-t border-gray-700/60 lg:px-8">
        {t('common.disclaimer')}
      </div>
      {showStatusBar && <StatusBar />}
    </div>
  )
}
