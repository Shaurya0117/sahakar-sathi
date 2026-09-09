import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ScrollReveal } from './MotionPrimitives'

const footerLinks = {
  Services: [
    { label: 'Electrical Repairs', to: '/customer' },
    { label: 'Plumbing', to: '/customer' },
    { label: 'Home Cleaning', to: '/customer' },
    { label: 'Carpentry', to: '/customer' },
    { label: 'AC Servicing', to: '/customer' },
  ],
  Platform: [
    { label: 'How It Works', to: '/' },
    { label: 'Join as Worker', to: '/register' },
    { label: 'Admin Portal', to: '/login' },
    { label: 'Service Catalog', to: '/customer' },
  ],
  Support: [
    { label: 'Help Center', to: '/' },
    { label: 'Contact Us', to: '/' },
    { label: 'WhatsApp Support', href: 'https://wa.me/919876543210?text=Hi' },
    { label: 'Helpline: 1800-266-7737', href: 'tel:18002667737' },
  ],
}

export default function Footer() {
  return (
    <footer className="bg-slate-900 text-slate-400 border-t border-slate-800 mt-auto">
      {/* Main Footer */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10">
          {/* Brand Column */}
          <ScrollReveal direction="up" delay={0}>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center font-bold text-lg shadow-lg shadow-blue-500/20">
                  🤝
                </div>
                <div>
                  <h3 className="font-extrabold text-white text-lg tracking-tight">Sahakar Sathi</h3>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Cooperative Portal</p>
                </div>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                A cooperative-owned digital portal connecting households with verified, 
                background-checked community workers. Fair pricing, equitable allocation, 
                zero predatory platform fees.
              </p>
              <div className="flex items-center gap-3 pt-2">
                <motion.a
                  href="https://wa.me/919876543210"
                  target="_blank"
                  rel="noreferrer"
                  className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-emerald-600 text-slate-400 hover:text-white flex items-center justify-center text-lg transition-colors border border-slate-700 hover:border-emerald-500"
                  whileHover={{ scale: 1.1, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  💬
                </motion.a>
                <motion.a
                  href="tel:18002667737"
                  className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-blue-600 text-slate-400 hover:text-white flex items-center justify-center text-lg transition-colors border border-slate-700 hover:border-blue-500"
                  whileHover={{ scale: 1.1, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  📞
                </motion.a>
                <motion.a
                  href="mailto:support@sahakarsathi.in"
                  className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-indigo-600 text-slate-400 hover:text-white flex items-center justify-center text-lg transition-colors border border-slate-700 hover:border-indigo-500"
                  whileHover={{ scale: 1.1, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  📧
                </motion.a>
              </div>
            </div>
          </ScrollReveal>

          {/* Link Columns */}
          {Object.entries(footerLinks).map(([heading, links], colIdx) => (
            <ScrollReveal key={heading} direction="up" delay={0.1 * (colIdx + 1)}>
              <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-widest mb-4">
                  {heading}
                </h4>
                <ul className="space-y-2.5">
                  {links.map((link) => (
                    <li key={link.label}>
                      {link.href ? (
                        <a
                          href={link.href}
                          target={link.href.startsWith('http') ? '_blank' : undefined}
                          rel={link.href.startsWith('http') ? 'noreferrer' : undefined}
                          className="text-xs text-slate-400 hover:text-white transition-colors flex items-center gap-1 group"
                        >
                          <span className="w-0 group-hover:w-2 h-0.5 bg-blue-500 rounded transition-all duration-300" />
                          {link.label}
                        </a>
                      ) : (
                        <Link
                          to={link.to}
                          className="text-xs text-slate-400 hover:text-white transition-colors flex items-center gap-1 group"
                        >
                          <span className="w-0 group-hover:w-2 h-0.5 bg-blue-500 rounded transition-all duration-300" />
                          {link.label}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-[11px] text-slate-500">
            © 2026 Labor Cooperative Society. All rights reserved.
          </p>
          <div className="flex items-center gap-4 text-[11px] text-slate-500">
            <span>Helpline: 1800-266-7737</span>
            <span className="w-1 h-1 rounded-full bg-slate-700" />
            <span>support@sahakarsathi.in</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
