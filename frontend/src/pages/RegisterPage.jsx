import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import PortalHeader from '../components/PortalHeader'
import Footer from '../components/Footer'
import AnimatedPage from '../components/AnimatedPage'
import { MotionButton } from '../components/MotionPrimitives'
import { register } from '../services/authService'

const ROLE_OPTIONS = [
  { value: 'CUSTOMER', label: 'Customer', icon: '🛒', desc: 'Request household services', color: 'border-blue-600 bg-blue-50 text-blue-900' },
  { value: 'WORKER', label: 'Worker Member', icon: '🛠️', desc: 'Offer skills & earn', color: 'border-emerald-600 bg-emerald-50 text-emerald-900' },
]

export default function RegisterPage() {
  const navigate = useNavigate()

  const [form, setForm] = useState({
    name: '', email: '', phone: '', password: '', confirmPassword: '', role: 'CUSTOMER',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  function selectRole(role) {
    setForm((prev) => ({ ...prev, role }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setLoading(true)
    try {
      await register({
        name: form.name,
        email: form.email,
        phone: form.phone || undefined,
        password: form.password,
        role: form.role,
      })
      navigate('/login', { state: { registered: true } })
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (status === 409) {
        setError('An account with this email already exists.')
      } else if (status === 422 && detail) {
        const msg = Array.isArray(detail) ? detail[0]?.msg ?? 'Validation error' : String(detail)
        setError(msg)
      } else {
        setError('Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const inputCls =
    'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition-shadow'

  return (
    <AnimatedPage className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <PortalHeader />

      <main className="flex-1 flex items-center justify-center p-4 py-8 relative overflow-hidden">
        {/* Decorative blobs */}
        <motion.div
          className="absolute top-20 -right-10 w-64 h-64 bg-emerald-200 rounded-full opacity-20 blur-3xl"
          animate={{ scale: [1, 1.2, 1], y: [0, -15, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute bottom-20 -left-10 w-48 h-48 bg-blue-200 rounded-full opacity-20 blur-3xl"
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
        />

        <motion.div
          className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6 sm:p-8 space-y-5 relative z-10"
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
              className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white flex items-center justify-center text-2xl shadow-lg shadow-emerald-500/20 mb-3"
              initial={{ scale: 0, rotate: 20 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20, delay: 0.3 }}
            >
              🚀
            </motion.div>
            <h1 className="text-2xl font-extrabold text-slate-900">Member Registration</h1>
            <p className="text-xs text-slate-500">Create a new cooperative portal account</p>
          </motion.div>

          {error && (
            <motion.div
              id="register-error"
              className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
            >
              ⚠️ {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Role Selection */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
            >
              <p className="text-xs font-bold text-slate-700 mb-1.5">Register account as:</p>
              <div className="grid grid-cols-2 gap-2">
                {ROLE_OPTIONS.map(({ value, label, icon, desc, color }) => (
                  <motion.button
                    key={value}
                    type="button"
                    onClick={() => selectRole(value)}
                    className={`p-2.5 rounded-xl border text-left transition-all ${
                      form.role === value
                        ? `${color} font-bold shadow-sm`
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <div className="text-base">{icon}</div>
                    <div className="text-xs">{label}</div>
                    <div className="text-[10px] text-slate-500 font-normal">{desc}</div>
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {[
              { id: 'reg-name', name: 'name', type: 'text', label: 'Full Name', placeholder: 'Rahul Kumar', delay: 0.3 },
              { id: 'reg-email', name: 'email', type: 'email', label: 'Email Address', placeholder: 'user@example.com', delay: 0.35 },
              { id: 'reg-phone', name: 'phone', type: 'tel', label: 'Phone Number', placeholder: '9876543210', delay: 0.4, optional: true },
              { id: 'reg-password', name: 'password', type: 'password', label: 'Password', placeholder: '••••••••', delay: 0.45, hint: '(min 8 characters)' },
              { id: 'reg-confirm', name: 'confirmPassword', type: 'password', label: 'Confirm Password', placeholder: '••••••••', delay: 0.5 },
            ].map((field) => (
              <motion.div
                key={field.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: field.delay }}
              >
                <label htmlFor={field.id} className="block text-xs font-bold text-slate-700 mb-1">
                  {field.label}{' '}
                  {field.optional && <span className="text-slate-500 font-normal">(optional)</span>}
                  {field.hint && <span className="text-slate-500 font-normal">{field.hint}</span>}
                </label>
                <input
                  id={field.id}
                  name={field.name}
                  type={field.type}
                  required={!field.optional}
                  value={form[field.name]}
                  onChange={handleChange}
                  className={inputCls}
                  placeholder={field.placeholder}
                />
              </motion.div>
            ))}

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55 }}
            >
              <MotionButton
                id="register-submit"
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
                    Creating Account…
                  </span>
                ) : (
                  `Create ${form.role === 'WORKER' ? 'Worker' : 'Customer'} Account`
                )}
              </MotionButton>
            </motion.div>
          </form>

          <motion.p
            className="text-center text-xs text-slate-600 pt-1"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            Already have an account?{' '}
            <Link to="/login" className="text-blue-700 font-bold hover:underline">
              Sign In
            </Link>
          </motion.p>
        </motion.div>
      </main>

      <Footer />
    </AnimatedPage>
  )
}
