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

      {/* ── Urban Company Style Hero Section ────────────────────────── */}
      <section className="relative bg-white pt-24 pb-16 overflow-hidden border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          
          <div className="space-y-8 z-10">
            <motion.h1
              className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-[1.1]"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            >
              Home services <br />
              <span className="text-slate-900">at your doorstep</span>
            </motion.h1>

            <motion.div
              className="bg-white rounded-xl shadow-lg border border-slate-200 flex items-center p-2 max-w-lg"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.6 }}
            >
              <div className="flex-1 flex items-center px-4 border-r border-slate-200">
                <span className="text-slate-400 mr-2">📍</span>
                <select className="bg-transparent text-sm font-semibold text-slate-800 outline-none w-full">
                  <option>New Delhi</option>
                  <option>Noida</option>
                  <option>Gurgaon</option>
                </select>
              </div>
              <div className="flex-[2] flex items-center px-4">
                <span className="text-slate-400 mr-2">🔍</span>
                <input 
                  type="text" 
                  placeholder="Search for 'AC Repair'" 
                  className="bg-transparent text-sm text-slate-800 outline-none w-full"
                />
              </div>
            </motion.div>

            <motion.p
              className="text-slate-500 text-sm max-w-md leading-relaxed"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.6 }}
            >
              Sahakar Sathi connects households with verified, background-checked community workers. Enjoy fair pricing and transparent allocation.
            </motion.p>
          </div>

          <motion.div
            className="relative z-10 hidden md:flex justify-end"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4, duration: 0.8 }}
          >
            <div className="relative">
              <div className="absolute inset-0 bg-blue-100 rounded-full blur-[80px] opacity-60 translate-x-10 translate-y-10"></div>
              <img 
                src="https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&q=80&w=600&h=600" 
                alt="Professional Worker" 
                className="relative rounded-3xl object-cover w-[450px] h-[450px] shadow-2xl border-8 border-white"
              />
              <div className="absolute -bottom-6 -left-6 bg-white p-4 rounded-xl shadow-xl border border-slate-100 flex items-center gap-4">
                <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center text-xl font-bold">★</div>
                <div>
                  <div className="text-lg font-extrabold text-slate-900">4.8/5</div>
                  <div className="text-xs text-slate-500">Average Worker Rating</div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Service Categories Section ─────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 flex-1 w-full space-y-16">
        <ScrollReveal direction="up">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-extrabold text-slate-900">What are you looking for?</h2>
            </div>
          </div>

          <motion.div
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-6"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-50px' }}
          >
            {serviceCategories.map((svc, idx) => (
              <Link to="/customer" key={idx}>
                <motion.div
                  variants={fadeInUp}
                  whileHover={{
                    y: -6,
                    boxShadow: '0 10px 25px rgba(0,0,0,0.05)',
                  }}
                  whileTap={{ scale: 0.95 }}
                  className="bg-white rounded-2xl flex flex-col items-center justify-center p-6 cursor-pointer border border-transparent hover:border-slate-100 transition-all text-center h-full group shadow-sm"
                >
                  <motion.div
                    className="w-16 h-16 rounded-2xl bg-slate-50 text-3xl flex items-center justify-center mb-4 shadow-inner group-hover:bg-blue-50 transition-colors"
                  >
                    {svc.icon}
                  </motion.div>
                  <h3 className="font-bold text-slate-800 text-sm leading-snug group-hover:text-blue-600 transition-colors">{svc.title}</h3>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </ScrollReveal>

        {/* ── Multi-Channel Booking Section ─────────────────────────── */}
        <ScrollReveal direction="up" delay={0.1}>
          <div className="bg-gradient-to-br from-blue-900 to-blue-950 rounded-3xl p-8 sm:p-12 shadow-2xl relative overflow-hidden">
            <motion.div
              className="absolute top-0 right-0 -mt-20 -mr-20 w-64 h-64 bg-blue-500 rounded-full blur-3xl opacity-20 pointer-events-none"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
            />

            <ScrollReveal direction="down" className="text-center max-w-2xl mx-auto space-y-3 mb-10">
              <h2 className="text-3xl font-extrabold text-white">3 Ways to Book a Service</h2>
              <p className="text-sm text-blue-200">
                Sahakar Sathi supports three convenient channels for booking household & community service workers. All requests are processed through our central cooperative system.
              </p>
            </ScrollReveal>

            <motion.div
              className="grid grid-cols-1 md:grid-cols-3 gap-6"
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
            >
              {/* Channel 1: Web Portal */}
              <motion.div
                variants={fadeInUp}
                whileHover={{ y: -6, scale: 1.02 }}
                className="bg-white/10 backdrop-blur-md p-6 rounded-2xl border border-white/20 shadow-xl flex flex-col justify-between space-y-6"
              >
                <div className="space-y-4 text-center">
                  <FloatingElement amplitude={5} delay={0}>
                    <div className="w-14 h-14 mx-auto rounded-full bg-blue-500/20 text-blue-300 text-2xl flex items-center justify-center font-bold border border-blue-500/30">
                      🌐
                    </div>
                  </FloatingElement>
                  <h3 className="font-bold text-white text-lg">Website Portal</h3>
                  <p className="text-xs text-blue-200 leading-relaxed">
                    Browse catalog, select dates, use GPS, and manage active service requests online.
                  </p>
                </div>
                <Link to="/customer">
                  <MotionButton className="w-full text-center py-2.5 px-4 bg-white hover:bg-blue-50 text-blue-900 font-bold text-sm rounded-xl transition">
                    Request Online ➔
                  </MotionButton>
                </Link>
              </motion.div>

              {/* Channel 2: WhatsApp */}
              <motion.div
                variants={fadeInUp}
                whileHover={{ y: -6, scale: 1.02 }}
                className="bg-emerald-900/50 backdrop-blur-md p-6 rounded-2xl border border-emerald-500/30 shadow-xl flex flex-col justify-between space-y-6"
              >
                <div className="space-y-4 text-center">
                  <FloatingElement amplitude={5} delay={0.5}>
                    <div className="w-14 h-14 mx-auto rounded-full bg-emerald-500/20 text-emerald-300 text-2xl flex items-center justify-center font-bold border border-emerald-500/30">
                      💬
                    </div>
                  </FloatingElement>
                  <h3 className="font-bold text-white text-lg">WhatsApp Bot</h3>
                  <p className="text-xs text-emerald-100/80 leading-relaxed">
                    Send a text or drop a location pin on WhatsApp. Interactive assistant guides you through.
                  </p>
                </div>
                <a href="https://wa.me/919876543210?text=Hi" target="_blank" rel="noreferrer">
                  <MotionButton className="w-full text-center py-2.5 px-4 bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-sm rounded-xl transition shadow-lg shadow-emerald-500/30">
                    Message on WhatsApp
                  </MotionButton>
                </a>
              </motion.div>

              {/* Channel 3: Phone IVR */}
              <motion.div
                variants={fadeInUp}
                whileHover={{ y: -6, scale: 1.02 }}
                className="bg-white/5 backdrop-blur-md p-6 rounded-2xl border border-white/10 shadow-xl flex flex-col justify-between space-y-6"
              >
                <div className="space-y-4 text-center">
                  <FloatingElement amplitude={5} delay={1}>
                    <div className="w-14 h-14 mx-auto rounded-full bg-white/10 text-slate-300 text-2xl flex items-center justify-center font-bold border border-white/20">
                      📞
                    </div>
                  </FloatingElement>
                  <h3 className="font-bold text-white text-lg">Call IVR Helpline</h3>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Call our toll-free cooperative helpline. Follow prompts to log service requests effortlessly.
                  </p>
                </div>
                <a href="tel:18001232667">
                  <MotionButton className="w-full text-center py-2.5 px-4 bg-slate-700 hover:bg-slate-600 text-white font-bold text-sm rounded-xl transition">
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
