import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import { LanguageProvider } from './context/LanguageContext'
import ProtectedRoute from './components/ProtectedRoute'
import { AnimatePresence } from 'framer-motion'

// Public pages
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import NotFoundPage from './pages/NotFoundPage'

// Protected dashboard pages
import AdminDashboardPage from './pages/AdminDashboardPage'
import WorkerDashboardPage from './pages/WorkerDashboardPage'
import CustomerDashboardPage from './pages/CustomerDashboardPage'

function AnimatedRoutes() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* ── Public routes ──────────────────────────────────────── */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* ── Protected routes — role-specific ───────────────────── */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="ADMIN">
              <AdminDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/worker"
          element={
            <ProtectedRoute requiredRole="WORKER">
              <WorkerDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/customer"
          element={
            <ProtectedRoute requiredRole="CUSTOMER">
              <CustomerDashboardPage />
            </ProtectedRoute>
          }
        />

        {/* ── 404 Catch-all ──────────────────────────────────────── */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AnimatePresence>
  )
}

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <BrowserRouter>
          <Toaster
            position="top-center"
            toastOptions={{
              duration: 4000,
              style: {
                borderRadius: '12px',
                background: '#1e293b',
                color: '#f1f5f9',
                fontSize: '13px',
                fontWeight: '500',
                padding: '12px 16px',
                boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
              },
              success: {
                iconTheme: { primary: '#10b981', secondary: '#fff' },
              },
              error: {
                iconTheme: { primary: '#ef4444', secondary: '#fff' },
              },
            }}
          />
          <AnimatedRoutes />
        </BrowserRouter>
      </AuthProvider>
    </LanguageProvider>
  )
}
