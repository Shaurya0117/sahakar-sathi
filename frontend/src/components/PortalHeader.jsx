import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../context/AuthContext'

export default function PortalHeader() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <motion.header
      className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-40"
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Official Tricolor Top Accent Strip */}
      <div className="h-1 bg-gradient-to-r from-amber-500 via-slate-200 to-emerald-600" />

      {/* Main Header Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
        {/* Brand Identity */}
        <Link to="/" className="flex items-center gap-3 text-slate-900 group">
          <motion.div
            className="w-10 h-10 rounded-lg bg-gradient-to-br from-slate-800 to-slate-900 text-white flex items-center justify-center font-bold text-lg shadow-sm border border-slate-700"
            whileHover={{ scale: 1.1, rotate: 5 }}
            whileTap={{ scale: 0.95 }}
          >
            🤝
          </motion.div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-xl tracking-tight text-slate-900">CoopServe</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full border border-slate-300">
                Cooperative Portal
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">Cooperative Community Services Platform</p>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-700">
          {[
            { to: '/', label: 'Home', show: true },
            { to: user?.role === 'CUSTOMER' ? '/customer' : '/', label: 'Services', show: true },
            { to: '/customer#requests', label: 'My Requests', show: user?.role === 'CUSTOMER', isAnchor: true },
            { to: '/worker', label: 'Worker Workspace', show: user?.role === 'WORKER' },
            { to: '/admin', label: 'Admin Portal', show: user?.role === 'ADMIN' },
          ].filter(i => i.show).map((item) => (
            <motion.div key={item.label} whileHover={{ y: -1 }} whileTap={{ y: 1 }}>
              {item.isAnchor ? (
                <a href={item.to} className="hover:text-blue-700 transition relative group">
                  {item.label}
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-blue-600 rounded transition-all group-hover:w-full" />
                </a>
              ) : (
                <Link to={item.to} className="hover:text-blue-700 transition relative group">
                  {item.label}
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-blue-600 rounded transition-all group-hover:w-full" />
                </Link>
              )}
            </motion.div>
          ))}
          <motion.button
            whileHover={{ y: -1 }}
            whileTap={{ y: 1 }}
            onClick={() => {
              import('react-hot-toast').then(({ default: toast }) => {
                toast('CoopServe Helpline: 1800-COOP-SERVE\nAvailable 8 AM - 8 PM', {
                  icon: '📞',
                  duration: 6000,
                })
              })
            }}
            className="hover:text-blue-700 transition relative group"
          >
            Help & Support
            <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-blue-600 rounded transition-all group-hover:w-full" />
          </motion.button>
        </nav>

        {/* User Account Section */}
        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="hidden sm:block text-right">
                <div className="text-xs font-bold text-slate-800">{user.name}</div>
                <div className="text-[10px] font-medium text-slate-500 uppercase">{user.role} Member</div>
              </div>
              <motion.button
                onClick={handleLogout}
                className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg border border-slate-300 transition"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                Sign Out
              </motion.button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login">
                <motion.button
                  className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg border border-slate-300 transition"
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                >
                  Sign In
                </motion.button>
              </Link>
              <Link to="/register">
                <motion.button
                  className="px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white text-xs font-semibold rounded-lg shadow-sm transition"
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                >
                  Register
                </motion.button>
              </Link>
            </div>
          )}

          {/* Mobile menu button */}
          <motion.button
            className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg bg-slate-100 border border-slate-200"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            whileTap={{ scale: 0.9 }}
          >
            <span className="text-lg">{mobileMenuOpen ? '✕' : '☰'}</span>
          </motion.button>
        </div>
      </div>

      {/* Mobile Navigation */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            className="md:hidden bg-white border-t border-slate-200 px-4 py-3 space-y-2"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Link to="/" onClick={() => setMobileMenuOpen(false)}
              className="block py-2 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 rounded-lg">Home</Link>
            <Link to={user?.role === 'CUSTOMER' ? '/customer' : '/'} onClick={() => setMobileMenuOpen(false)}
              className="block py-2 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 rounded-lg">Services</Link>
            {user?.role === 'CUSTOMER' && (
              <a href="/customer#requests" onClick={() => setMobileMenuOpen(false)}
                className="block py-2 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 rounded-lg">My Requests</a>
            )}
            {user?.role === 'WORKER' && (
              <Link to="/worker" onClick={() => setMobileMenuOpen(false)}
                className="block py-2 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 rounded-lg">Worker Workspace</Link>
            )}
            {user?.role === 'ADMIN' && (
              <Link to="/admin" onClick={() => setMobileMenuOpen(false)}
                className="block py-2 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 rounded-lg">Admin Portal</Link>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  )
}
