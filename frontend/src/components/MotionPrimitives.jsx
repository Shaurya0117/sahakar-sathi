import { motion } from 'framer-motion'

// Stagger container for animating lists of children
export const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
}

// Fade up for individual items in a stagger list
export const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.22, 1, 0.36, 1],
    },
  },
}

// Scale in for cards/modals
export const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 25,
    },
  },
}

// Slide in from left
export const slideInLeft = {
  hidden: { opacity: 0, x: -30 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.5,
      ease: [0.22, 1, 0.36, 1],
    },
  },
}

// Slide in from right
export const slideInRight = {
  hidden: { opacity: 0, x: 30 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.5,
      ease: [0.22, 1, 0.36, 1],
    },
  },
}

// Pop in effect
export const popIn = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      type: 'spring',
      stiffness: 600,
      damping: 20,
    },
  },
}

// Blur in effect
export const blurIn = {
  hidden: { opacity: 0, filter: 'blur(10px)' },
  visible: {
    opacity: 1,
    filter: 'blur(0px)',
    transition: { duration: 0.6, ease: 'easeOut' },
  },
}

// MotionCard — a reusable animated card wrapper
export function MotionCard({ children, className = '', delay = 0, hover = true, ...props }) {
  return (
    <motion.div
      className={className}
      variants={fadeInUp}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-50px' }}
      transition={{ delay }}
      whileHover={
        hover
          ? {
              y: -4,
              boxShadow: '0 20px 40px rgba(0,0,0,0.08), 0 0 0 1px rgba(59,130,246,0.1)',
              transition: { duration: 0.2 },
            }
          : undefined
      }
      whileTap={hover ? { scale: 0.98 } : undefined}
      {...props}
    >
      {children}
    </motion.div>
  )
}

// MotionButton — adds micro-interactions to buttons
export function MotionButton({ children, className = '', variant = 'default', ...props }) {
  const tapScale = variant === 'icon' ? 0.85 : 0.97
  const hoverScale = variant === 'icon' ? 1.1 : 1.02

  return (
    <motion.button
      className={className}
      whileHover={{ scale: hoverScale }}
      whileTap={{ scale: tapScale }}
      transition={{ type: 'spring', stiffness: 500, damping: 25 }}
      {...props}
    >
      {children}
    </motion.button>
  )
}

// Counter animation for stats
export function AnimatedCounter({ value, duration = 1.5 }) {
  return (
    <motion.span
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      key={value}
    >
      <motion.span
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {value}
      </motion.span>
    </motion.span>
  )
}

// Floating animation wrapper
export function FloatingElement({ children, className = '', delay = 0, amplitude = 10 }) {
  return (
    <motion.div
      className={className}
      animate={{ y: [-amplitude, amplitude, -amplitude] }}
      transition={{
        duration: 4,
        ease: 'easeInOut',
        repeat: Infinity,
        delay,
      }}
    >
      {children}
    </motion.div>
  )
}

// Reveal on scroll wrapper
export function ScrollReveal({ children, className = '', direction = 'up', delay = 0 }) {
  const directionMap = {
    up: { y: 40 },
    down: { y: -40 },
    left: { x: 40 },
    right: { x: -40 },
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, ...directionMap[direction] }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{
        duration: 0.6,
        delay,
        ease: [0.22, 1, 0.36, 1],
      }}
    >
      {children}
    </motion.div>
  )
}
