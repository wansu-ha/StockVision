import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import StockList from './pages/StockList'
import StockDetail from './pages/StockDetail'
import Trading from './pages/Trading'
import ExecutionLog from './pages/ExecutionLog'
import StrategyBuilder from './pages/StrategyBuilder'
import Portfolio from './pages/Portfolio'
import Templates from './pages/Templates'
import AdminDashboard from './pages/AdminDashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Onboarding from './pages/Onboarding'
import Layout from './components/Layout'
import ToastContainer from './components/ToastContainer'
import { AuthProvider } from './context/AuthContext'

// React Query 클라이언트 생성
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <ToastContainer />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="*" element={
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/stocks" element={<StockList />} />
                  <Route path="/stocks/:symbol" element={<StockDetail />} />
                  <Route path="/trading" element={<Trading />} />
                  <Route path="/logs" element={<ExecutionLog />} />
                  <Route path="/strategy" element={<StrategyBuilder />} />
                  <Route path="/portfolio" element={<Portfolio />} />
                  <Route path="/templates" element={<Templates />} />
                  <Route path="/admin" element={<AdminDashboard />} />
                </Routes>
              </Layout>
            } />
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
