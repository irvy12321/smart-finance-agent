import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './components/ui/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'
import Sidebar from './components/Sidebar'

// Pages
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Research from './pages/Research'
import Report from './pages/Report'
import SystemOverview from './pages/SystemOverview'
import Chat from './pages/Chat'
import RAGManagement from './pages/RAGManagement'

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <AuthProvider>
          <ErrorBoundary>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Protected routes */}
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <div className="flex h-screen bg-dark-bg">
                      <Sidebar />
                      <main className="flex-1 overflow-auto">
                        <ErrorBoundary>
                        <Routes>
                          <Route path="/" element={<Dashboard />} />
                          <Route path="/research" element={<Research />} />
                          <Route path="/chat" element={<Chat />} />
                          <Route path="/rag" element={<RAGManagement />} />
                          <Route path="/report/:taskId" element={<Report />} />
                          <Route path="/system" element={<SystemOverview />} />
                        </Routes>
                        </ErrorBoundary>
                      </main>
                    </div>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </ErrorBoundary>
        </AuthProvider>
      </ToastProvider>
    </Router>
  )
}

export default App
