import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import PortalHeader from '../components/PortalHeader'
import Footer from '../components/Footer'
import AnimatedPage from '../components/AnimatedPage'
import {
  MotionCard,
  MotionButton,
  ScrollReveal,
  FloatingElement,
  staggerContainer,
  fadeInUp,
} from '../components/MotionPrimitives'

export default function LandingPage() {
  const serviceCategories = [
    { title: "Women's Salon, Spa & Laser", icon: '💅', count: 'Beauty & Wellness', color: 'from-pink-500 to-rose-600' },
    { title: "Men's Salon & Massage", icon: '✂️', count: 'Grooming & Spa', color: 'from-slate-600 to-slate-800' },
    { title: "AC & Appliance Repair", icon: '❄️', count: 'AC, Fridge, Washing Machine', color: 'from-sky-500 to-blue-600' },
    { title: "Cleaning & Pest Control", icon: '🧹', count: 'Deep Cleaning, Cockroach', color: 'from-emerald-500 to-teal-600' },
    { title: "Electrician, Plumber, Carpenter", icon: '🔧', count: 'Wiring, Leaks, Furniture', color: 'from-amber-500 to-orange-600' },
    { title: "Painting & Waterproofing", icon: '🎨', count: 'Home Painting, Damp Proofing', color: 'from-purple-500 to-indigo-600' },
  ]

  const stats = [
    { label: 'Active Cooperative Network', value: 'Ghaziabad Community Coop' },
    { label: 'Verified Worker Pool', value: '100% Background Checked', badge: '✓' },
    { label: 'Workload Distribution Model', value: 'Smart Equitable Allocation' },
    { label: 'Predatory Platform Fees', value: '0% (Worker-Owned)', highlight: true },
  ]

  return (
    <AnimatedPage className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <PortalHeader />

      {/* ── Premium Cooperative Hero Section ────────────────────────── */}
      <section className="relative bg-cream-50 pt-32 pb-24 overflow-hidden">
        {/* Ambient Animated Blobs */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
          <div className="absolute top-[-10%] left-[-5%] w-96 h-96 bg-emerald-200/40 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-float" style={{ animationDuration: '7s' }}></div>
          <div className="absolute top-[20%] right-[-5%] w-[30rem] h-[30rem] bg-amber-100/50 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-float" style={{ animationDuration: '9s', animationDelay: '1s' }}></div>
          <div className="absolute bottom-[-10%] left-[20%] w-[25rem] h-[25rem] bg-teal-100/50 rounded-full mix-blend-multiply filter blur-3xl opacity-60 animate-float" style={{ animationDuration: '8s', animationDelay: '2s' }}></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative z-10">
          
          {/* Left: Typography & Value Prop */}
          <div className="space-y-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-block px-4 py-1.5 rounded-full bg-emerald-100/50 border border-emerald-200/50 backdrop-blur-md"
            >
              <span className="text-emerald-800 text-sm font-bold tracking-wide">🏆 Fair & Transparent Cooperative</span>
            </motion.div>

            <motion.h1
              className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-900 leading-[1.05]"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            >
              Expert services by <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500">
                your local community
              </span>
            </motion.h1>

            <motion.p
              className="text-slate-600 text-lg max-w-lg leading-relaxed font-medium"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.6 }}
            >
              Skip the corporate middleman. Sahakar Sathi connects you directly with skilled, verified neighborhood professionals. 100% fair pricing, 0% predatory fees.
            </motion.p>

            <motion.div
              className="flex flex-col sm:flex-row gap-4 pt-2"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.6 }}
            >
              <Link to="/customer">
                <MotionButton className="w-full sm:w-auto px-8 py-4 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-2xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2">
                  Book a Service <span className="text-xl">→</span>
                </MotionButton>
              </Link>
              <Link to="/register">
                <MotionButton className="w-full sm:w-auto px-8 py-4 bg-white hover:bg-slate-50 text-slate-800 border border-slate-200 font-bold rounded-2xl shadow-sm hover:shadow-md transition-all flex items-center justify-center gap-2">
                  Join as Worker
                </MotionButton>
              </Link>
            </motion.div>
          </div>

          {/* Right: Floating Glass Profile Cards Collage */}
          <motion.div
            className="relative hidden lg:block h-[500px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 1 }}
          >
            {/* Center Main Card */}
            <motion.div 
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 w-72 glass-card p-5 animate-float"
              style={{ animationDelay: '0s' }}
            >
              <div className="flex gap-4 items-center mb-4">
                <img src="https://images.unsplash.com/photo-1607990281513-2c110a25bd8c?auto=format&fit=crop&q=80&w=150&h=150" alt="Plumber" className="w-16 h-16 rounded-full object-cover border-2 border-white shadow-sm" />
                <div>
                  <h3 className="font-bold text-slate-900 text-lg">Rajesh K.</h3>
                  <p className="text-emerald-600 font-medium text-sm">Master Plumber</p>
                </div>
              </div>
              <div className="flex justify-between items-center bg-white/50 rounded-xl p-3 border border-white/60">
                <div>
                  <div className="text-xs text-slate-500">Trust Score</div>
                  <div className="font-bold text-slate-900">98/100</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-500">Rating</div>
                  <div className="font-bold text-slate-900 flex items-center gap-1">4.9 <span className="text-amber-500">★</span></div>
                </div>
              </div>
            </motion.div>

            {/* Top Right Card */}
            <motion.div 
              className="absolute top-4 right-0 z-10 w-56 glass-card p-4 animate-float"
              style={{ animationDelay: '1.5s', animationDuration: '5s' }}
            >
              <div className="flex gap-3 items-center">
                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-600 text-xl border border-white shadow-sm">⚡</div>
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">Sita Devi</h3>
                  <p className="text-slate-500 text-xs">Electrician</p>
                </div>
              </div>
            </motion.div>

            {/* Bottom Left Card */}
            <motion.div 
              className="absolute bottom-10 left-4 z-30 w-64 glass-card p-4 animate-float"
              style={{ animationDelay: '2.5s', animationDuration: '6s' }}
            >
              <div className="flex gap-3 items-center mb-2">
                <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center text-teal-600 text-xl border border-white shadow-sm">🧹</div>
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">Amit Singh</h3>
                  <p className="text-slate-500 text-xs">Deep Cleaning</p>
                </div>
              </div>
              <div className="w-full bg-white/50 rounded-full h-1.5 mt-3 overflow-hidden">
                <div className="bg-emerald-500 w-3/4 h-full rounded-full"></div>
              </div>
              <p className="text-[10px] text-slate-500 mt-1 text-right">Job Progress</p>
            </motion.div>

          </motion.div>
        </div>
      </section>

      {/* ── Service Categories Section ─────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 flex-1 w-full space-y-24">
        <ScrollReveal direction="up">
          <div className="flex flex-col items-center text-center mb-12">
            <h2 className="text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">Our Services</h2>
            <div className="w-24 h-1.5 bg-emerald-500 rounded-full mb-4"></div>
            <p className="text-slate-600 max-w-2xl font-medium">From deep cleaning to expert electrical work, our cooperative members are fully vetted and ready to help.</p>
          </div>

          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-50px' }}
          >
            {serviceCategories.map((svc, idx) => (
              <Link to="/customer" key={idx}>
                <motion.div
                  variants={fadeInUp}
                  whileHover={{ y: -8 }}
                  whileTap={{ scale: 0.98 }}
                  className="relative overflow-hidden bg-white rounded-3xl p-6 border border-slate-200 cursor-pointer group shadow-sm hover:shadow-2xl transition-all duration-300"
                >
                  <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${svc.color} opacity-10 rounded-full blur-2xl group-hover:opacity-20 transition-opacity translate-x-10 -translate-y-10`}></div>
                  <div className="flex items-start gap-4 relative z-10">
                    <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${svc.color} text-white text-2xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                      {svc.icon}
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900 text-lg mb-1 group-hover:text-emerald-700 transition-colors">{svc.title}</h3>
                      <p className="text-slate-500 text-sm font-medium">{svc.count}</p>
                    </div>
                  </div>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </ScrollReveal>

        {/* ── Multi-Channel Booking Section ─────────────────────────── */}
        {/* ── Multi-Channel Booking Section ─────────────────────────── */}
        <ScrollReveal direction="up" delay={0.1}>
          <div className="bg-primary-950 rounded-[3rem] p-10 sm:p-16 shadow-2xl relative overflow-hidden">
            <motion.div
              className="absolute top-0 right-0 -mt-20 -mr-20 w-96 h-96 bg-primary-700 rounded-full blur-3xl opacity-30 pointer-events-none"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
            />
            <motion.div
              className="absolute bottom-0 left-0 -mb-20 -ml-20 w-80 h-80 bg-accent-600 rounded-full blur-3xl opacity-20 pointer-events-none"
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
            />

            <ScrollReveal direction="down" className="text-center max-w-2xl mx-auto space-y-4 mb-16 relative z-10">
              <span className="text-accent-400 font-bold tracking-widest uppercase text-sm">Inclusive Technology</span>
              <h2 className="text-4xl font-extrabold text-white">Book Anywhere, Anytime</h2>
              <p className="text-base text-primary-100 font-light">
                Sahakar Sathi supports three convenient channels for booking household & community service workers. No app installation required.
              </p>
            </ScrollReveal>

            <motion.div
              className="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10"
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
            >
              {/* Channel 1: Web Portal */}
              <motion.div
                variants={fadeInUp}
                whileHover={{ y: -8, scale: 1.02 }}
                className="bg-white/10 backdrop-blur-xl p-8 rounded-3xl border border-white/20 shadow-xl flex flex-col justify-between space-y-8 group"
              >
                <div className="space-y-5 text-center">
                  <FloatingElement amplitude={5} delay={0}>
                    <div className="w-16 h-16 mx-auto rounded-full bg-white/20 text-white text-3xl flex items-center justify-center font-bold border border-white/30 group-hover:bg-white group-hover:text-primary-900 transition-all duration-300">
                      🌐
                    </div>
                  </FloatingElement>
                  <h3 className="font-bold text-white text-xl">Website Portal</h3>
                  <p className="text-sm text-primary-100/80 leading-relaxed font-light">
                    Browse catalog, select dates, use GPS, and manage active service requests online.
                  </p>
                </div>
                <Link to="/customer">
                  <MotionButton className="w-full text-center py-3 px-4 bg-white hover:bg-cream-50 text-primary-900 font-bold text-sm rounded-xl transition shadow-lg">
                    Request Online ➔
                  </MotionButton>
                </Link>
              </motion.div>

              {/* Channel 2: WhatsApp */}
              <motion.div
                variants={fadeInUp}
                whileHover={{ y: -8, scale: 1.02 }}
                className="bg-accent-600/20 backdrop-blur-xl p-8 rounded-3xl border border-accent-400/30 shadow-xl flex flex-col justify-between space-y-8 group"
              >
                <div className="space-y-5 text-center">
                  <FloatingElement amplitude={5} delay={0.5}>
                    <div className="w-16 h-16 mx-auto rounded-full bg-accent-500/30 text-accent-100 text-3xl flex items-center justify-center font-bold border border-accent-400/50 group-hover:bg-accent-500 group-hover:text-white transition-all duration-300">
                      💬
                    </div>
                  </FloatingElement>
                  <h3 className="font-bold text-white text-xl">WhatsApp Bot</h3>
                  <p className="text-sm text-accent-100/80 leading-relaxed font-light">
                    Send a text or drop a location pin on WhatsApp. Interactive assistant guides you through.
                  </p>
                </div>
                <a href="https://wa.me/919876543210?text=Hi" target="_blank" rel="noreferrer">
                  <MotionButton className="w-full text-center py-3 px-4 bg-accent-500 hover:bg-accent-600 text-white font-bold text-sm rounded-xl transition shadow-lg shadow-accent-500/30">
                    Message on WhatsApp
                  </MotionButton>
                </a>
              </motion.div>

              {/* Channel 3: Phone IVR */}
              <motion.div
                variants={fadeInUp}
                whileHover={{ y: -8, scale: 1.02 }}
                className="bg-white/5 backdrop-blur-xl p-8 rounded-3xl border border-white/10 shadow-xl flex flex-col justify-between space-y-8 group"
              >
                <div className="space-y-5 text-center">
                  <FloatingElement amplitude={5} delay={1}>
                    <div className="w-16 h-16 mx-auto rounded-full bg-white/10 text-slate-300 text-3xl flex items-center justify-center font-bold border border-white/20 group-hover:bg-white/30 transition-all duration-300">
                      📞
                    </div>
                  </FloatingElement>
                  <h3 className="font-bold text-white text-xl">Call IVR Helpline</h3>
                  <p className="text-sm text-slate-300 leading-relaxed font-light">
                    Call our toll-free cooperative helpline. Follow prompts to log service requests effortlessly.
                  </p>
                </div>
                <a href="tel:18001232667">
                  <MotionButton className="w-full text-center py-3 px-4 bg-white/20 hover:bg-white/30 text-white font-bold text-sm rounded-xl transition backdrop-blur-md">
                    1800-123-COOP
                  </MotionButton>
                </a>
              </motion.div>
            </motion.div>
          </div>
        </ScrollReveal>

        {/* ── How It Works ────────────────────────────────────────── */}
        <ScrollReveal direction="up" delay={0.15}>
          <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-8 text-center">
              How Cooperative Service Allocation Works
            </h2>
            <motion.div
              className="grid grid-cols-1 md:grid-cols-4 gap-6 text-center"
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
            >
              {[
                { step: 1, title: 'Submit Request', desc: 'Customer enters location and service requirements', icon: '📝' },
                { step: 2, title: 'Cooperative Allocation', desc: 'Cooperative matches verified worker based on skill, location & workload', icon: '🤝' },
                { step: 3, title: 'Service Delivery', desc: 'Assigned worker accepts job and carries out service', icon: '🔧' },
                { step: 4, title: 'Fair Completion', desc: 'Direct payment to worker with zero predatory platform cuts', icon: '✅' },
              ].map((item) => (
                <motion.div
                  key={item.step}
                  variants={fadeInUp}
                  className="space-y-3 group"
                  whileHover={{ y: -4 }}
                >
                  <motion.div
                    className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-100 to-blue-50 text-2xl flex items-center justify-center mx-auto shadow-sm border border-blue-100 group-hover:shadow-lg group-hover:shadow-blue-100 transition-shadow"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    transition={{ type: 'spring', stiffness: 400 }}
                  >
                    {item.icon}
                  </motion.div>
                  <div className="flex items-center justify-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                      {item.step}
                    </span>
                    <h4 className="font-bold text-slate-900 text-sm">{item.title}</h4>
                  </div>
                  <p className="text-xs text-slate-500">{item.desc}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </ScrollReveal>
      </main>

      <Footer />
    </AnimatedPage>
  )
}
