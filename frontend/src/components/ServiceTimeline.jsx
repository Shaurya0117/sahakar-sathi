import { motion } from 'framer-motion'

const steps = [
  { key: 'PENDING', label: 'Request Submitted', icon: '📋', color: 'amber' },
  { key: 'ALLOCATED', label: 'Worker Assigned', icon: '👷', color: 'blue' },
  { key: 'ACCEPTED', label: 'Worker Accepted', icon: '✅', color: 'emerald' },
  { key: 'IN_PROGRESS', label: 'Service In Progress', icon: '⚙️', color: 'indigo' },
  { key: 'COMPLETED', label: 'Service Completed', icon: '🎉', color: 'emerald' },
]

function getStepIndex(requestStatus, bookingStatus) {
  if (requestStatus === 'CANCELLED') return -1

  if (bookingStatus === 'COMPLETED') return 4
  if (bookingStatus === 'IN_PROGRESS') return 3
  if (bookingStatus === 'ACCEPTED') return 2
  if (bookingStatus === 'ASSIGNED') return 1
  // PENDING request with no booking
  return 0
}

const colorMap = {
  amber: {
    bg: 'bg-amber-100',
    border: 'border-amber-400',
    text: 'text-amber-700',
    line: 'bg-amber-400',
    glow: 'shadow-amber-200',
  },
  blue: {
    bg: 'bg-blue-100',
    border: 'border-blue-400',
    text: 'text-blue-700',
    line: 'bg-blue-400',
    glow: 'shadow-blue-200',
  },
  emerald: {
    bg: 'bg-emerald-100',
    border: 'border-emerald-400',
    text: 'text-emerald-700',
    line: 'bg-emerald-400',
    glow: 'shadow-emerald-200',
  },
  indigo: {
    bg: 'bg-indigo-100',
    border: 'border-indigo-400',
    text: 'text-indigo-700',
    line: 'bg-indigo-400',
    glow: 'shadow-indigo-200',
  },
}

export default function ServiceTimeline({ requestStatus, bookingStatus, createdAt }) {
  const currentStep = getStepIndex(requestStatus, bookingStatus)

  if (requestStatus === 'CANCELLED') {
    return (
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex items-center gap-2 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3"
      >
        <span className="text-lg">❌</span>
        <div>
          <p className="text-xs font-bold text-rose-700">Request Cancelled</p>
          <p className="text-[10px] text-rose-500">This service request has been cancelled</p>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="py-2">
      <div className="flex items-center gap-1 mb-3">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Service Progress</span>
        {currentStep < 4 && (
          <motion.span
            className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 ml-1"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}
      </div>

      <div className="relative">
        {/* Steps */}
        <div className="flex items-start justify-between relative">
          {steps.map((step, idx) => {
            const isCompleted = idx <= currentStep
            const isCurrent = idx === currentStep
            const colors = colorMap[step.color]

            return (
              <div key={step.key} className="flex flex-col items-center relative z-10" style={{ flex: 1 }}>
                {/* Connector line (before this step) */}
                {idx > 0 && (
                  <div
                    className="absolute top-4 right-1/2 h-0.5 w-full -z-10"
                    style={{ transform: 'translateX(-50%)' }}
                  >
                    <motion.div
                      className={`h-full ${idx <= currentStep ? colors.line : 'bg-slate-200'}`}
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{ delay: idx * 0.15, duration: 0.4, ease: 'easeOut' }}
                      style={{ transformOrigin: 'left' }}
                    />
                  </div>
                )}

                {/* Step circle */}
                <motion.div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 transition-all
                    ${isCompleted
                      ? `${colors.bg} ${colors.border} ${isCurrent ? `shadow-lg ${colors.glow}` : ''}`
                      : 'bg-slate-100 border-slate-300 text-slate-400'
                    }`}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{
                    delay: idx * 0.12,
                    type: 'spring',
                    stiffness: 500,
                    damping: 25,
                  }}
                  whileHover={{ scale: 1.15 }}
                >
                  {isCompleted ? (
                    <span>{step.icon}</span>
                  ) : (
                    <span className="text-[10px] font-bold text-slate-400">{idx + 1}</span>
                  )}
                </motion.div>

                {/* Pulse ring for current step */}
                {isCurrent && currentStep < 4 && (
                  <motion.div
                    className={`absolute top-0 w-8 h-8 rounded-full ${colors.border} border-2`}
                    animate={{ scale: [1, 1.6], opacity: [0.6, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
                  />
                )}

                {/* Label */}
                <motion.p
                  className={`text-[10px] font-semibold mt-2 text-center leading-tight max-w-[70px]
                    ${isCompleted ? colors.text : 'text-slate-400'}`}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.12 + 0.1 }}
                >
                  {step.label}
                </motion.p>
              </div>
            )
          })}
        </div>

        {/* Background connector track */}
        <div className="absolute top-4 left-[10%] right-[10%] h-0.5 bg-slate-200 -z-0" />
      </div>
    </div>
  )
}
