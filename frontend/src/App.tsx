import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Research from './pages/Research'
import Report from './pages/Report'
import SystemOverview from './pages/SystemOverview'
import Chat from './pages/Chat'
import Sidebar from './components/Sidebar'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  return (
    <Router>
      <ErrorBoundary>
        <div className="flex h-screen bg-dark-bg">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/research" element={<Research />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/report/:taskId" element={<Report />} />
                <Route path="/system" element={<SystemOverview />} />
              </Routes>
            </ErrorBoundary>
          </main>
        </div>
      </ErrorBoundary>
    </Router>
  )
}

export default App
