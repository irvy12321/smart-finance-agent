import { Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './components/ui/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'
import { MainLayout } from './components/layout'

const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const ResearchCenter = lazy(() => import('./pages/ResearchCenter'))
const Chat = lazy(() => import('./pages/Chat'))
const KnowledgeBase = lazy(() => import('./pages/KnowledgeBase'))
const RAGManagement = lazy(() => import('./pages/RAGManagement'))
const Portfolio = lazy(() => import('./pages/Portfolio'))
const SystemOverview = lazy(() => import('./pages/SystemOverview'))
const Report = lazy(() => import('./pages/Report'))
const WorkflowVisualization = lazy(() => import('./pages/Workflow'))

function PageFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-dark-bg text-primary-300">
      Loading...
    </div>
  )
}

function App() {
  return (
    <Router>
      <ToastProvider>
        <AuthProvider>
          <ErrorBoundary>
            <Suspense fallback={<PageFallback />}>
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
            </Suspense>
          </ErrorBoundary>
        </AuthProvider>
      </ToastProvider>
    </Router>
  )
}

export default App
