import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './components/ui/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'
import { MainLayout } from './components/layout'

// Pages
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import ResearchCenter from './pages/ResearchCenter'
import Chat from './pages/Chat'
import KnowledgeBase from './pages/KnowledgeBase'
import RAGManagement from './pages/RAGManagement'
import Portfolio from './pages/Portfolio'
import SystemOverview from './pages/SystemOverview'
import Report from './pages/Report'
import WorkflowVisualization from './pages/Workflow'

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

              {/* Protected routes with MainLayout */}
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <MainLayout>
                      <ErrorBoundary>
                        <Routes>
                          {/* All roles can access */}
                          <Route path="/" element={<Dashboard />} />
                          <Route path="/report/:taskId" element={<Report />} />
                          <Route path="/system" element={<SystemOverview />} />
                          <Route path="/portfolio" element={<Portfolio />} />

                          {/* Admin and Analyst only */}
                          <Route path="/research" element={<ResearchCenter />} />
                          <Route path="/chat" element={<Chat />} />
                          <Route path="/knowledge" element={<KnowledgeBase />} />
                          <Route path="/rag" element={<RAGManagement />} />
                        </Routes>
                      </ErrorBoundary>
                    </MainLayout>
                  </ProtectedRoute>
                }
              />

              {/* Full-screen workflow visualization */}
              <Route
                path="/workflow/:taskId"
                element={
                  <ProtectedRoute>
                    <WorkflowVisualization />
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
