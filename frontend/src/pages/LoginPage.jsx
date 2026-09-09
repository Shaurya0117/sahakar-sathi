import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import PortalHeader from '../components/PortalHeader'
import Footer from '../components/Footer'
import AnimatedPage from '../components/AnimatedPage'
import { MotionButton } from '../components/MotionPrimitives'
import { useAuth } from '../context/AuthContext'

const ROLE_HOME = {
  ADMIN: '/admin',
  WORKER: '/worker',
  CUSTOMER: '/customer',
}

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function performLogin(targetEmail, targetPassword) {
    setError('')
    setLoading(true)

    try {
      const user = await login(targetEmail, targetPassword)
      navigate(ROLE_HOME[user.role] ?? '/', { replace: true })
    } catch (err) {
      const status = err.response?.status
      if (status === 401) {
        setError('Incorrect email or password. Please try again.')
      } else if (status === 403) {
        setError('Your account has been deactivated. Contact the cooperative.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    await performLogin(email, password)
  }

  const demoAccounts = [
    { label: 'Customer', sub: 'Asha Sharma', email: 'asha.customer@coopserve.demo', password: 'Customer@1234', color: 'bg-blue-50 hover:bg-blue-100 text-blue-800 border-blue-200', icon: '🛒' },
    { label: 'Admin', sub: 'Coop Admin', email: 'admin@coopserve.demo', password: 'Admin@1234', color: 'bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300', icon: '🛡️' },
    { label: 'Worker', sub: 'Rahul Kumar', email: 'rahul.electrician@coopserve.demo', password: 'Worker@1234', color: 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-200', icon: '🛠️' },
  ]

  return (
    <AnimatedPage className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <PortalHeader />

      <main className="flex-1 flex items-center justify-center p-4 relative overflow-hidden">
        {/* Decorative blobs */}
        <motion.div
          className="absolute top-10 -left-20 w-72 h-72 bg-blue-200 rounded-full opacity-20 blur-3xl"
          animate={{ scale: [1, 1.15, 1], x: [0, 15, 0] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute bottom-10 -right-20 w-56 h-56 bg-indigo-200 rounded-full opacity-20 blur-3xl"
          animate={{ scale: [1, 1.2, 1], y: [0, -20, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        />

        <motion.div
          className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6 sm:p-8 space-y-6 relative z-10"
          initial={{ opacity: 0, y: 30, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          <motion.div
            className="text-center space-y-1"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <motion.div
              className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center text-2xl shadow-lg shadow-blue-500/20 mb-3"
              initial={{ scale: 0, rotate: -20 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20, delay: 0.3 }}
            >
              🤝
            </motion.div>
            <h1 className="text-2xl font-extrabold text-slate-900">Member Sign In</h1>
            <p className="text-xs text-slate-500">Access your cooperative service account</p>
          </motion.div>

          {error && (
            <motion.div
              id="login-error"
              className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              transition={{ duration: 0.3 }}
            >
              ⚠️ {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
            >
              <label htmlFor="login-email" className="block text-xs font-bold text-slate-700 mb-1">
                Email Address
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition-shadow"
                placeholder="user@example.com"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
            >
              <label htmlFor="login-password" className="block text-xs font-bold text-slate-700 mb-1">
                Password
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition-shadow"
                placeholder="••••••••"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <MotionButton
                id="login-submit"
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-sm transition disabled:opacity-50 shadow-lg shadow-blue-500/20"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <motion.div
                      className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                      animate={{ rotate: 360 }}
                      transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                    />
                    Signing in…
                  </span>
                ) : (
                  'Sign In'
                )}
              </MotionButton>
            </motion.div>
          </form>

          {/* Quick Demo Credentials */}
          <motion.div
            className="pt-4 border-t border-slate-200 text-xs"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            <p className="text-slate-500 font-bold uppercase tracking-wider text-[10px] mb-2 text-center">
              ⚡ Quick Demo Account Sign-In (1-Click)
            </p>
            <div className="grid grid-cols-3 gap-2">
              {demoAccounts.map((acct) => (
                <MotionButton
                  key={acct.label}
                  type="button"
                  onClick={() => {
                    setEmail(acct.email)
                    setPassword(acct.password)
                    performLogin(acct.email, acct.password)
                  }}
                  className={`p-2.5 rounded-xl border text-center transition ${acct.color}`}
                >
                  <div className="text-base mb-0.5">{acct.icon}</div>
                  <div className="font-bold text-[11px]">{acct.label}</div>
                  <div className="text-[9px] text-slate-600 truncate">{acct.sub}</div>
                </MotionButton>
              ))}
            </div>
          </motion.div>

          <motion.p
            className="text-center text-xs text-slate-600 pt-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
          >
            Don't have an account?{' '}
            <Link to="/register" className="text-blue-700 font-bold hover:underline">
              Create a Member Account
            </Link>
          </motion.p>
        </motion.div>
      </main>

      <Footer />
    </AnimatedPage>
  )
}
