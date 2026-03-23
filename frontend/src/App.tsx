import { lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import StockList from './pages/StockList'
import ExecutionLog from './pages/ExecutionLog'
import StrategyBuilder from './pages/StrategyBuilder'
import StrategyList from './pages/StrategyList'
import Settings from './pages/Settings'
const AdminLayout = lazy(() => import('./pages/Admin'))
const AdminDash = lazy(() => import('./pages/Admin/Dashboard'))
const AdminUsers = lazy(() => import('./pages/Admin/Users'))
const AdminStats = lazy(() => import('./pages/Admin/Stats'))
const AdminServiceKeys = lazy(() => import('./pages/Admin/ServiceKeys'))
const AdminTemplates = lazy(() => import('./pages/Admin/Templates'))
const AdminAiMonitor = lazy(() => import('./pages/Admin/AiMonitor'))
const AdminErrorLogs = lazy(() => import('./pages/Admin/ErrorLogs'))
const AdminLogin = lazy(() => import('./pages/Admin/Login'))
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
const ProtoA = lazy(() => import('./pages/ProtoA'))
const ProtoB = lazy(() => import('./pages/ProtoB'))
const ProtoC = lazy(() => import('./pages/ProtoC'))
import MainDashboard from './pages/MainDashboard'
import OnboardingWizard from './pages/OnboardingWizard'
import Layout from './components/Layout'
import AlertContainer from './components/AlertContainer'
import ToastContainer from './components/ToastContainer'
import AdminGuard from './components/AdminGuard'
import ConsentGate from './components/ConsentGate'
import OAuthCallback from './pages/OAuthCallback'
import LegalDocument from './pages/LegalDocument'
import ErrorBoundary from './components/ErrorBoundary'
import { AuthProvider, useAuth } from './context/AuthContext'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

/** 인증 필수 라우트 가드 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  // DEV: 서버 없이 UI 확인용 bypass
  if (import.meta.env.DEV && import.meta.env.VITE_AUTH_BYPASS === 'true') return <>{children}</>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <ConsentGate>{children}</ConsentGate>
}

function AppRoutes() {
  const location = useLocation()
  return (
    <ErrorBoundary key={location.pathname}>
    <Routes>
      {/* 공개 라우트 */}
      <Route path="/admin/login" element={<Suspense fallback={null}><AdminLogin /></Suspense>} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
      <Route path="/legal/:type" element={<LegalDocument />} />
      {import.meta.env.DEV && (
        <>
          <Route path="/proto-a" element={<Suspense fallback={null}><ProtoA /></Suspense>} />
          <Route path="/proto-b" element={<Suspense fallback={null}><ProtoB /></Suspense>} />
          <Route path="/proto-c" element={<Suspense fallback={null}><ProtoC /></Suspense>} />
        </>
      )}

      {/* 메인 대시보드 (Layout 없음 — 자체 헤더 사용) */}
      <Route path="/" element={
        <ProtectedRoute>
          <MainDashboard />
        </ProtectedRoute>
      } />

      {/* 온보딩 (Layout 없음) */}
      <Route path="/onboarding" element={
        <ProtectedRoute>
          <OnboardingWizard />
        </ProtectedRoute>
      } />

      {/* 설정 (Layout 없음 — 자체 헤더 사용) */}
      <Route path="/settings" element={
        <ProtectedRoute>
          <Settings />
        </ProtectedRoute>
      } />

      {/* 인증 필수 라우트 (Layout 포함) */}
      <Route path="*" element={
        <ProtectedRoute>
          <Layout>
            <Routes>
              <Route path="/stocks" element={<StockList />} />
              <Route path="/logs" element={<ExecutionLog />} />
              <Route path="/strategies" element={<StrategyList />} />
              <Route path="/strategies/new" element={<StrategyBuilder />} />
              <Route path="/strategies/:id/edit" element={<StrategyBuilder />} />
              <Route path="/strategy" element={<StrategyBuilder />} />
              <Route path="/admin" element={<AdminGuard><Suspense fallback={null}><AdminLayout /></Suspense></AdminGuard>}>
                <Route index element={<Suspense fallback={null}><AdminDash /></Suspense>} />
                <Route path="users" element={<Suspense fallback={null}><AdminUsers /></Suspense>} />
                <Route path="stats" element={<Suspense fallback={null}><AdminStats /></Suspense>} />
                <Route path="service-keys" element={<Suspense fallback={null}><AdminServiceKeys /></Suspense>} />
                <Route path="templates" element={<Suspense fallback={null}><AdminTemplates /></Suspense>} />
                <Route path="ai" element={<Suspense fallback={null}><AdminAiMonitor /></Suspense>} />
                <Route path="errors" element={<Suspense fallback={null}><AdminErrorLogs /></Suspense>} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Layout>
        </ProtectedRoute>
      } />
    </Routes>
    </ErrorBoundary>
  )
}

// PWA: Service Worker 등록
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // SW 등록 실패 — 무시 (PWA 미지원 환경)
    })
  })
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Router>
            <AlertContainer />
            <ToastContainer />
            <AppRoutes />
          </Router>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
