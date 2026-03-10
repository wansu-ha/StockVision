import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import StockList from './pages/StockList'
import StockDetail from './pages/StockDetail'
import Trading from './pages/Trading'
import ExecutionLog from './pages/ExecutionLog'
import StrategyBuilder from './pages/StrategyBuilder'
import StrategyList from './pages/StrategyList'
import Portfolio from './pages/Portfolio'
import Templates from './pages/Templates'
import Settings from './pages/Settings'
import AdminDashboard from './pages/AdminDashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Onboarding from './pages/Onboarding'
import ProtoA from './pages/ProtoA'
import ProtoB from './pages/ProtoB'
import ProtoC from './pages/ProtoC'
import MainDashboard from './pages/MainDashboard'
import Layout from './components/Layout'
import AlertContainer from './components/AlertContainer'
import ToastContainer from './components/ToastContainer'
import AdminGuard from './components/AdminGuard'
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
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      {/* 공개 라우트 */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/proto-a" element={<ProtoA />} />
      <Route path="/proto-b" element={<ProtoB />} />
      <Route path="/proto-c" element={<ProtoC />} />

      {/* 메인 대시보드 (Layout 없음 — 자체 헤더 사용) */}
      <Route path="/" element={
        <ProtectedRoute>
          <MainDashboard />
        </ProtectedRoute>
      } />

      {/* 설정 (Layout 없음 — 자체 헤더 사용) */}
      <Route path="/settings" element={
        <ProtectedRoute>
          <Settings />
        </ProtectedRoute>
      } />

      {/* 인증 필수 라우트 (레거시 Layout) */}
      <Route path="*" element={
        <ProtectedRoute>
          <Layout>
            <Routes>
              <Route path="/legacy-dashboard" element={<Dashboard />} />
              <Route path="/stocks" element={<StockList />} />
              <Route path="/stocks/:symbol" element={<StockDetail />} />
              <Route path="/trading" element={<Trading />} />
              <Route path="/logs" element={<ExecutionLog />} />
              <Route path="/strategies" element={<StrategyList />} />
              <Route path="/strategies/new" element={<StrategyBuilder />} />
              <Route path="/strategies/:id/edit" element={<StrategyBuilder />} />
              <Route path="/strategy" element={<StrategyBuilder />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/templates" element={<Templates />} />
              <Route path="/admin/*" element={<AdminGuard><AdminDashboard /></AdminGuard>} />
            </Routes>
          </Layout>
        </ProtectedRoute>
      } />
    </Routes>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <AlertContainer />
          <ToastContainer />
          <AppRoutes />
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
