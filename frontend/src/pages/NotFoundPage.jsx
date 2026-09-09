import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import PortalHeader from '../components/PortalHeader'
import AnimatedPage from '../components/AnimatedPage'
import { FloatingElement } from '../components/MotionPrimitives'

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <PortalHeader />

      <AnimatedPage className="flex-1 flex items-center justify-center p-4">
        <div className="text-center max-w-lg mx-auto space-y-6">
          {/* Animated 404 Illustration */}
          <FloatingElement amplitude={15}>
            <motion.div
              className="text-[120px] leading-none font-extrabold text-transparent bg-clip-text bg-gradient-to-br from-blue-600 via-indigo-500 to-purple-600 select-none"
              initial={{ scale: 0, rotate: -10 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
            >
              404
            </motion.div>
          </FloatingElement>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="space-y-3"
          >
            <h1 className="text-2xl font-extrabold text-slate-900">
              Page Not Found
            </h1>
            <p className="text-sm text-slate-500 max-w-sm mx-auto leading-relaxed">
              The page you're looking for doesn't exist or has been moved. 
              Let's get you back to the cooperative portal.
            </p>
          </motion.div>

          <motion.div
            className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.5 }}
          >
            <Link to="/">
              <motion.button
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold text-sm rounded-xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-shadow"
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.97 }}
              >
                ← Back to Home
              </motion.button>
            </Link>
            <Link to="/login">
              <motion.button
                className="px-6 py-3 bg-white text-slate-700 font-semibold text-sm rounded-xl border border-slate-300 hover:border-slate-400 transition-colors"
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.97 }}
              >
                Sign In
              </motion.button>
            </Link>
          </motion.div>

          {/* Decorative blobs */}
          <div className="relative mt-12">
            <motion.div
              className="absolute -top-20 -left-20 w-40 h-40 bg-blue-200 rounded-full opacity-20 blur-3xl"
              animate={{ scale: [1, 1.2, 1], x: [0, 20, 0] }}
              transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            />
            <motion.div
              className="absolute -top-10 -right-20 w-32 h-32 bg-purple-200 rounded-full opacity-20 blur-3xl"
              animate={{ scale: [1, 1.3, 1], y: [0, -15, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
            />
          </div>
        </div>
      </AnimatedPage>
    </div>
  )
}
