import { ReactNode } from 'react'
import TopNavBar from './TopNavBar'
import StatusBar from './StatusBar'

interface MainLayoutProps {
  children: ReactNode
  showStatusBar?: boolean
}

export default function MainLayout({ children, showStatusBar = true }: MainLayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-dark-bg">
      <TopNavBar />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
      {showStatusBar && <StatusBar />}
    </div>
  )
}
