/**
 * ProtectedRoute — guards routes by authentication and optional role.
 *
 * Usage:
 *   <ProtectedRoute>                       — any authenticated user
 *   <ProtectedRoute requiredRole="ADMIN">  — ADMIN only
 *
 * Unauthenticated → /login
 * Wrong role      → role's own dashboard (or /unauthorized if none)
 */
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const ROLE_HOME = {
  ADMIN:    '/admin',
  WORKER:   '/worker',
  CUSTOMER: '/customer',
}

export default function ProtectedRoute({ children, requiredRole }) {
  const { isAuthenticated, user, loading } = useAuth()

  // While restoring session, render nothing (prevents flash of redirect)
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRole && user?.role !== requiredRole) {
    // Redirect to the user's own dashboard
    const home = ROLE_HOME[user?.role] ?? '/'
    return <Navigate to={home} replace />
  }

  return children
}
