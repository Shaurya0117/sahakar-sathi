import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import LocationPicker from '../components/LocationPicker'
import PortalHeader from '../components/PortalHeader'
import Footer from '../components/Footer'
import AnimatedPage from '../components/AnimatedPage'
import { PageSkeleton } from '../components/Skeleton'
import {
  MotionCard,
  MotionButton,
  ScrollReveal,
  staggerContainer,
  fadeInUp,
} from '../components/MotionPrimitives'
import { useAuth } from '../context/AuthContext'
import { useWorkerProfile } from '../hooks/useWorkerProfile'
import {
  acceptJob,
  completeJob,
  getWorkerJobs,
  rejectJob,
  startJob,
} from '../services/bookingService'
import { createWorkerProfile, updateWorkerProfile } from '../services/workerService'
import { useLanguage } from '../context/LanguageContext'
import toast from 'react-hot-toast'

const PRESET_SKILLS = [
  'Wiring', 'Fan Repair', 'Switch Repair', 'Plumbing',
  'Pipe Fitting', 'Carpentry', 'Appliance Repair', 'Painting',
  'AC Servicing', 'Cleaning', 'Gardening'
]

export default function WorkerDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { profile, loading, error: fetchError, hasProfile, refresh } = useWorkerProfile()
  const { t, language, setLanguage } = useLanguage()

  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState('')
  const [jobs, setJobs] = useState([])
  const [jobsLoading, setJobsLoading] = useState(false)
  
  // Voice feature states
  const [isDictating, setIsDictating] = useState(null) // holds job id
  const [jobNotes, setJobNotes] = useState({}) // { jobId: 'note' }

  const fetchWorkerJobs = useCallback(async () => {
    setJobsLoading(true)
    try {
      const res = await getWorkerJobs()
      setJobs(res.data || [])
    } catch {
      // Ignore background fetch error
    } finally {
      setJobsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (hasProfile) fetchWorkerJobs()
  }, [hasProfile, fetchWorkerJobs])

  const handleAcceptJob = async (bookingId) => {
    try {
      await acceptJob(bookingId)
      setSuccessMsg('Job accepted successfully!')
      await fetchWorkerJobs()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to accept job.')
    }
  }

  const handleRejectJob = async (bookingId) => {
    try {
      await rejectJob(bookingId)
      setSuccessMsg('Job rejected. The request has been returned to cooperative pending status.')
      await fetchWorkerJobs()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reject job.')
    }
  }

  const handleStartJob = async (bookingId) => {
    try {
      await startJob(bookingId)
      setSuccessMsg('Service started! Job is now In Progress.')
      await fetchWorkerJobs()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start service.')
    }
  }

  const handleCompleteJob = async (bookingId) => {
    try {
      await completeJob(bookingId)
      setSuccessMsg('Service completed successfully!')
      await fetchWorkerJobs()
      await refresh()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to complete service.')
    }
  }

  // Voice & WhatsApp Features
  const handleReadAloud = (job) => {
    if (!('speechSynthesis' in window)) {
      toast.error('Voice synthesis not supported in this browser.')
      return
    }
    const text = `Job for ${job.service_name}. Category: ${job.service_category}. Location: ${job.location}. Customer is ${job.customer_name}. Scheduled on ${job.scheduled_date} at ${job.scheduled_time}.`
    const utterance = new SpeechSynthesisUtterance(text)
    // Attempt to set language
    utterance.lang = language === 'hi' ? 'hi-IN' : language === 'mr' ? 'mr-IN' : 'en-US'
    window.speechSynthesis.speak(utterance)
    toast('Reading job details...', { icon: '🔊' })
  }

  const handleDictateNote = (jobId) => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      toast.error('Speech recognition not supported in this browser.')
      return
    }
    if (isDictating === jobId) {
      setIsDictating(null)
      toast.success('Dictation stopped.')
      return
    }
    const recognition = new SpeechRecognition()
    recognition.lang = language === 'hi' ? 'hi-IN' : language === 'mr' ? 'mr-IN' : 'en-US'
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      setJobNotes(prev => ({ ...prev, [jobId]: (prev[jobId] || '') + ' ' + transcript }))
      toast.success('Note added via voice.')
    }
    recognition.onend = () => {
      if (isDictating === jobId) setIsDictating(null)
    }

    recognition.start()
    setIsDictating(jobId)
    toast('Listening...', { icon: '🎤' })
  }

  const handleWhatsApp = (job) => {
    const phone = job.customer_phone || '919999999999'
    const msg = `Hello ${job.customer_name}, I am your cooperative service worker for the ${job.service_name} job scheduled on ${job.scheduled_date}.`
    window.open(`https://wa.me/${phone}?text=${encodeURIComponent(msg)}`, '_blank')
  }

  // Form fields
  const [profession, setProfession] = useState('')
  const [experienceYears, setExperienceYears] = useState(0)
  const [location, setLocation] = useState('')
  const [latitude, setLatitude] = useState(null)
  const [longitude, setLongitude] = useState(null)
  const [skills, setSkills] = useState([])
  const [newSkillInput, setNewSkillInput] = useState('')
  const [availability, setAvailability] = useState('AVAILABLE')
  const [availabilityDesc, setAvailabilityDesc] = useState('')

  const startEdit = () => {
    if (profile) {
      setProfession(profile.profession || '')
      setExperienceYears(profile.experience_years ?? 0)
      setLocation(profile.location || '')
      setLatitude(profile.latitude ?? null)
      setLongitude(profile.longitude ?? null)
      setSkills(profile.skills || [])
      setAvailability(profile.availability || 'AVAILABLE')
      setAvailabilityDesc(profile.availability_description || '')
    } else {
      setProfession(''); setExperienceYears(0); setLocation(''); setLatitude(null); setLongitude(null)
      setSkills([]); setAvailability('AVAILABLE'); setAvailabilityDesc('')
    }
    setError(null); setSuccessMsg(''); setIsEditing(true)
  }

  const addSkill = (skillToAdd) => {
    const trimmed = skillToAdd.trim()
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]); setNewSkillInput('')
    }
  }

  const removeSkill = (skillToRemove) => setSkills(skills.filter((s) => s !== skillToRemove))

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true); setError(null); setSuccessMsg('')
    const payload = {
      profession, experience_years: Number(experienceYears), location, latitude, longitude,
      skills, availability, availability_description: availabilityDesc || undefined,
    }
    try {
      if (hasProfile) {
        await updateWorkerProfile(payload); setSuccessMsg('Worker profile updated successfully!')
      } else {
        await createWorkerProfile(payload); setSuccessMsg('Worker profile created successfully!')
      }
      await refresh(); setIsEditing(false)
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to save profile.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally { setSaving(false) }
  }

  const handleQuickToggleAvailability = async () => {
    if (!profile) return
    const nextStatus = profile.availability === 'AVAILABLE' ? 'UNAVAILABLE' : 'AVAILABLE'
    try {
      await updateWorkerProfile({ availability: nextStatus }); await refresh()
    } catch { /* Ignore */ }
  }

  const inputCls = 'w-full px-3 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-xs focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition'

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
        <PortalHeader />
        <PageSkeleton cards={4} />
      </div>
    )
  }

  return (
    <AnimatedPage className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <PortalHeader />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-6">

        {/* Worker Header */}
        <motion.div
          className="relative bg-gradient-to-br from-indigo-900 to-slate-900 p-8 rounded-2xl shadow-xl overflow-hidden flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 text-white"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <motion.div
            className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none text-8xl"
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          >
            🛠️
          </motion.div>
          
          {/* Language Selector */}
          <div className="absolute top-4 right-4 z-20">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-white/10 backdrop-blur-md text-white text-xs font-bold border border-white/20 rounded-xl px-3 py-1.5 outline-none hover:bg-white/20 transition cursor-pointer"
            >
              <option value="en" className="text-slate-900">English</option>
              <option value="hi" className="text-slate-900">हिंदी (Hindi)</option>
              <option value="mr" className="text-slate-900">मराठी (Marathi)</option>
            </select>
          </div>

          <div className="relative z-10 flex items-center gap-6 mt-4 sm:mt-0">
            <motion.div
              className="w-16 h-16 rounded-2xl bg-white/10 backdrop-blur-md text-3xl flex items-center justify-center border border-white/20 shadow-inner"
              whileHover={{ scale: 1.1, rotate: 5 }}
            >
              🛠️
            </motion.div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="bg-indigo-500/20 text-indigo-300 font-bold text-[10px] px-2.5 py-1 rounded-full border border-indigo-400/30 tracking-wider uppercase">
                  {t('worker.workspace')}
                </span>
                {profile && <VerificationBadge status={profile.verification_status} t={t} />}
              </div>
              <motion.h1
                className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-indigo-200"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                {user?.name}
              </motion.h1>
              <p className="text-sm text-indigo-200 mt-0.5">{user?.email}</p>
            </div>
          </div>

          {profile && (
            <motion.div
              className="relative z-10 bg-white/10 backdrop-blur-md px-6 py-4 rounded-xl border border-white/20 text-center min-w-[150px]"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 }}
              whileHover={{ scale: 1.05 }}
            >
              <div className="text-xs text-indigo-200 font-semibold uppercase tracking-widest mb-1">{t('profile.strength')}</div>
              <div className="text-3xl font-extrabold text-white">{profile.profile_completion}%</div>
            </motion.div>
          )}
        </motion.div>

        {/* Banners */}
        <AnimatePresence>
          {fetchError && (
            <motion.div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs"
              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
              ⚠️ {fetchError}
            </motion.div>
          )}
          {successMsg && (
            <motion.div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between"
              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
              <span>✓ {successMsg}</span>
              <MotionButton variant="icon" onClick={() => setSuccessMsg('')} className="text-emerald-600 font-bold">✕</MotionButton>
            </motion.div>
          )}
          {error && (
            <motion.div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between"
              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
              <span>⚠️ {error}</span>
              <MotionButton variant="icon" onClick={() => setError(null)} className="text-rose-600 font-bold">✕</MotionButton>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main Content */}
        {!hasProfile && !isEditing ? (
          <motion.div
            className="bg-white p-10 text-center space-y-4 border border-slate-200 rounded-2xl"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <motion.div className="text-4xl" animate={{ y: [0, -5, 0] }} transition={{ duration: 2, repeat: Infinity }}>📋</motion.div>
            <h2 className="text-lg font-bold text-slate-900">Set Up Your Worker Profile</h2>
            <p className="text-xs text-slate-600 max-w-md mx-auto">Enter your profession, skills, experience, and service area location to receive job allocations.</p>
            <MotionButton onClick={startEdit}
              className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-bold text-xs rounded-xl shadow-lg shadow-blue-500/20 transition">
              Create Profile Now →
            </MotionButton>
          </motion.div>
        ) : isEditing ? (
          <motion.div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h2 className="text-base font-bold text-slate-900">{hasProfile ? 'Edit Worker Profile' : 'Create Worker Profile'}</h2>
              {hasProfile && <MotionButton onClick={() => setIsEditing(false)} className="text-xs text-slate-500 hover:text-slate-800">Cancel</MotionButton>}
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <motion.div initial={{ opacity: 0, x: -15 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Profession <span className="text-rose-600">*</span></label>
                  <input type="text" required value={profession} onChange={(e) => setProfession(e.target.value)}
                    placeholder="e.g. Electrician, Plumber, Carpenter" className={inputCls} />
                </motion.div>
                <motion.div initial={{ opacity: 0, x: -15 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 }}>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Experience (Years) <span className="text-rose-600">*</span></label>
                  <input type="number" min="0" max="60" required value={experienceYears} onChange={(e) => setExperienceYears(e.target.value)} className={inputCls} />
                </motion.div>
              </div>

              <LocationPicker locationValue={location} latitudeValue={latitude} longitudeValue={longitude}
                onChange={({ location: loc, latitude: lat, longitude: lon }) => { setLocation(loc); setLatitude(lat); setLongitude(lon) }} />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Availability</label>
                  <select value={availability} onChange={(e) => setAvailability(e.target.value)} className={inputCls}>
                    <option value="AVAILABLE">AVAILABLE — Ready for jobs</option>
                    <option value="UNAVAILABLE">UNAVAILABLE — Taking time off</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Working Hours Note</label>
                  <input type="text" value={availabilityDesc} onChange={(e) => setAvailabilityDesc(e.target.value)}
                    placeholder="e.g. Mon-Sat, 9:00 AM - 6:00 PM" className={inputCls} />
                </div>
              </div>

              {/* Skills Tag Editor */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Skills & Services</label>
                <div className="flex flex-wrap gap-2 mb-2 p-3 bg-slate-50 border border-slate-200 rounded-xl min-h-[40px] items-center">
                  {skills.length === 0 ? (
                    <span className="text-xs text-slate-400">No skills added yet</span>
                  ) : (
                    skills.map((s) => (
                      <motion.span key={s} className="bg-blue-50 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-blue-200 flex items-center gap-1"
                        initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}
                        layout transition={{ type: 'spring', stiffness: 500, damping: 25 }}>
                        {s}
                        <MotionButton type="button" variant="icon" onClick={() => removeSkill(s)} className="text-blue-600 font-bold hover:text-blue-900">×</MotionButton>
                      </motion.span>
                    ))
                  )}
                </div>
                <div className="flex gap-2">
                  <input type="text" value={newSkillInput} onChange={(e) => setNewSkillInput(e.target.value)}
                    placeholder="Add custom skill..." className="flex-1 px-3 py-1.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-xs outline-none" />
                  <MotionButton type="button" onClick={() => addSkill(newSkillInput)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-xl border border-slate-300">
                    + Add
                  </MotionButton>
                </div>
              </div>

              <div className="flex gap-3 pt-3 border-t border-slate-200">
                <MotionButton type="submit" disabled={saving}
                  className="flex-1 py-2.5 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-blue-700 text-xs transition disabled:opacity-50 shadow-sm">
                  {saving ? 'Saving Profile...' : 'Save Profile Changes'}
                </MotionButton>
                {hasProfile && (
                  <MotionButton type="button" onClick={() => setIsEditing(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-xl">Cancel</MotionButton>
                )}
              </div>
            </form>
          </motion.div>
        ) : (
          <motion.div className="space-y-6" variants={staggerContainer} initial="hidden" animate="visible">
            {/* Wallet Earnings Dashboard */}
            <motion.div variants={fadeInUp}
              className="bg-slate-900 p-6 rounded-2xl shadow-xl text-white flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden">
              <motion.div className="absolute top-0 right-0 p-4 text-slate-800 opacity-20 text-6xl pointer-events-none"
                animate={{ rotate: [0, 5, -5, 0] }} transition={{ duration: 6, repeat: Infinity }}>💰</motion.div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="bg-emerald-500/20 text-emerald-300 font-bold text-[10px] px-2 py-0.5 rounded-full border border-emerald-500/30 uppercase tracking-wider">Worker Wallet</span>
                  <span className="text-xs text-slate-400">Available to withdraw</span>
                </div>
                <motion.h2 className="text-4xl font-extrabold text-white mt-1"
                  initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3, type: 'spring' }}>
                  ${jobs.filter(b => b.status === 'COMPLETED').reduce((sum, b) => sum + (b.amount || 0), 0).toFixed(2)}
                </motion.h2>
              </div>
              <div className="flex gap-4">
                <motion.div className="bg-slate-800 p-3 rounded-xl min-w-[120px] border border-slate-700 text-center"
                  whileHover={{ scale: 1.05 }}>
                  <p className="text-[10px] text-slate-400 font-bold uppercase">Jobs Completed</p>
                  <p className="text-xl font-bold mt-1 text-emerald-400">{jobs.filter(b => b.status === 'COMPLETED').length}</p>
                </motion.div>
                <motion.div className="bg-slate-800 p-3 rounded-xl min-w-[120px] border border-slate-700 text-center"
                  whileHover={{ scale: 1.05 }}>
                  <p className="text-[10px] text-slate-400 font-bold uppercase">Expected Payout</p>
                  <p className="text-xl font-bold mt-1 text-amber-400">
                    ${jobs.filter(b => b.status === 'IN_PROGRESS' || b.status === 'ACCEPTED').reduce((sum, b) => sum + (b.amount || 0), 0).toFixed(2)}
                  </p>
                </motion.div>
              </div>
            </motion.div>

            {/* Profile Overview */}
            <motion.div variants={fadeInUp} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">{profile.profession || 'Professional'}</h2>
                  <p className="text-xs text-slate-500 mt-0.5">📍 {profile.location || 'Location not set'} • ⏱️ {profile.experience_years} Years Experience</p>
                </div>
                <MotionButton onClick={startEdit}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 text-xs font-semibold rounded-xl">
                  Edit Profile
                </MotionButton>
              </div>

              <div>
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {profile.skills?.length > 0 ? profile.skills.map((s) => (
                    <motion.span key={s} className="bg-blue-50 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-blue-200"
                      whileHover={{ scale: 1.05 }}>✓ {s}</motion.span>
                  )) : <span className="text-xs text-slate-400 italic">No skills listed</span>}
                </div>
              </div>

              <motion.div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-100 text-xs"
                variants={staggerContainer} initial="hidden" animate="visible">
                {[
                  { label: 'Availability', value: profile.availability,
                    action: <MotionButton onClick={handleQuickToggleAvailability} className="text-blue-700 text-[10px] underline">Toggle</MotionButton> },
                  { label: 'Verification', value: profile.verification_status },
                  { label: 'Rating', value: profile.rating > 0 ? `${profile.rating.toFixed(1)} ★` : 'Neutral', color: 'text-amber-700' },
                  { label: 'Jobs Completed', value: profile.total_jobs },
                ].map((stat) => (
                  <motion.div key={stat.label} variants={fadeInUp}
                    className="bg-slate-50 p-3 rounded-xl border border-slate-200"
                    whileHover={{ y: -2, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
                    <span className="text-slate-500">{stat.label}</span>
                    <div className={`font-bold mt-0.5 flex justify-between items-center ${stat.color || 'text-slate-900'}`}>
                      <span>{stat.value}</span>
                      {stat.action}
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>

            {/* Assigned Jobs */}
            <motion.div variants={fadeInUp} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h2 className="text-base font-bold text-slate-900">My Allocated Jobs</h2>
                  <p className="text-xs text-slate-500">Cooperative allocated service jobs awaiting your response or execution</p>
                </div>
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                  {jobs.length} Job(s)
                </span>
              </div>

              {jobsLoading ? (
                <div className="py-6 text-center text-xs text-slate-500">
                  <motion.div className="w-6 h-6 border-3 border-blue-600 border-t-transparent rounded-full mx-auto mb-2"
                    animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }} />
                  Loading jobs...
                </div>
              ) : jobs.length === 0 ? (
                <motion.div className="p-8 text-center text-slate-500 bg-slate-50 rounded-xl border border-slate-200 text-xs"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <motion.div className="text-3xl mb-2" animate={{ y: [0, -5, 0] }} transition={{ duration: 2, repeat: Infinity }}>📭</motion.div>
                  <p className="font-bold text-slate-800">No Jobs Allocated Currently</p>
                  <p className="mt-1">When cooperative administrators allocate a service request to you, it will appear here.</p>
                </motion.div>
              ) : (
                <motion.div className="grid grid-cols-1 md:grid-cols-2 gap-4"
                  variants={staggerContainer} initial="hidden" animate="visible">
                  {jobs.map((job) => (
                    <motion.div key={job.id} variants={fadeInUp}
                      whileHover={{ y: -3, boxShadow: '0 12px 30px rgba(0,0,0,0.06)' }}
                      className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3 transition-shadow">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono font-bold text-slate-400">Job #{job.id}</span>
                        <motion.span
                          className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
                            job.status === 'ASSIGNED' ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : job.status === 'ACCEPTED' ? 'bg-blue-100 text-blue-800 border border-blue-300'
                            : job.status === 'IN_PROGRESS' ? 'bg-indigo-100 text-indigo-800 border border-indigo-300'
                            : job.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            : 'bg-slate-100 text-slate-700'
                          }`}
                          initial={{ scale: 0 }} animate={{ scale: 1 }}
                          transition={{ type: 'spring', stiffness: 500, damping: 25 }}>
                          {job.status === 'ASSIGNED' ? '⏳ Awaiting Response' : job.status}
                        </motion.span>
                      </div>

                      <div>
                        <h3 className="font-bold text-slate-900 text-sm">{job.service_name}</h3>
                        <p className="text-xs text-slate-500">Category: {job.service_category}</p>
                      </div>

                      <div className="space-y-1 text-xs text-slate-700 bg-white p-3 rounded-xl border border-slate-200 relative">
                        <MotionButton 
                          onClick={() => handleReadAloud(job)} 
                          className="absolute top-2 right-2 p-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition"
                          title={t('read.aloud')}
                        >
                          🔊
                        </MotionButton>
                        <p>📍 <strong>{t('location')}:</strong> {job.location}</p>
                        <p>📅 <strong>{t('schedule')}:</strong> {job.scheduled_date} at {job.scheduled_time}</p>
                        <p>👤 <strong>{t('customer')}:</strong> {job.customer_name} ({job.customer_phone || 'No phone'})</p>
                        
                        {jobNotes[job.id] && (
                          <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-xs italic">
                            🎤 Note: {jobNotes[job.id]}
                          </div>
                        )}
                      </div>

                      {job.image_url && (
                        <div className="pt-2">
                          <p className="text-slate-500 font-bold uppercase text-[10px] mb-1">Attached Photo</p>
                          <img src={`http://localhost:8000${job.image_url}`} alt="Customer issue" className="max-h-48 rounded-xl border border-slate-200 object-cover" />
                        </div>
                      )}

                      <div className="pt-2 border-t border-slate-200 space-y-2">
                        {/* Status Actions */}
                        {job.status === 'ASSIGNED' && (
                          <div className="flex gap-2">
                            <MotionButton onClick={() => handleRejectJob(job.id)}
                              className="flex-1 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold rounded-xl">
                              {t('reject.job')}
                            </MotionButton>
                            <MotionButton onClick={() => handleAcceptJob(job.id)}
                              className="flex-1 py-2 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm">
                              {t('accept.job')}
                            </MotionButton>
                          </div>
                        )}
                        {job.status === 'ACCEPTED' && (
                          <MotionButton onClick={() => handleStartJob(job.id)}
                            className="w-full py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-bold text-xs rounded-xl shadow-sm">
                            {t('start.service')}
                          </MotionButton>
                        )}
                        {job.status === 'IN_PROGRESS' && (
                          <MotionButton onClick={() => handleCompleteJob(job.id)}
                            className="w-full py-2 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm">
                            {t('mark.completed')}
                          </MotionButton>
                        )}
                        {job.status === 'COMPLETED' && (
                          <div className="text-center text-xs font-bold text-emerald-800 bg-emerald-50 py-2 rounded-xl border border-emerald-200">
                            {t('job.completed')}
                          </div>
                        )}

                        {/* Worker Empowerment Actions */}
                        {(job.status === 'ACCEPTED' || job.status === 'IN_PROGRESS') && (
                          <div className="flex gap-2 pt-2 border-t border-slate-100">
                            <MotionButton onClick={() => handleWhatsApp(job)}
                              className="flex-1 py-1.5 bg-[#25D366]/10 hover:bg-[#25D366]/20 text-[#128C7E] border border-[#25D366]/30 text-[10px] font-bold rounded-lg flex items-center justify-center gap-1">
                              💬 {t('whatsapp.chat')}
                            </MotionButton>
                            <MotionButton onClick={() => handleDictateNote(job.id)}
                              className={`flex-1 py-1.5 border text-[10px] font-bold rounded-lg flex items-center justify-center gap-1 ${
                                isDictating === job.id 
                                  ? 'bg-rose-100 text-rose-700 border-rose-300 animate-pulse' 
                                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'
                              }`}>
                              {isDictating === job.id ? t('stop.dictation') : t('dictate.note')}
                            </MotionButton>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </motion.div>
          </motion.div>
        )}
      </main>

      <Footer />
    </AnimatedPage>
  )
}

function VerificationBadge({ status, t }) {
  const configs = {
    VERIFIED: { cls: 'bg-emerald-100 text-emerald-800 border-emerald-300', label: t ? t('verified.worker') : '✓ Verified Worker' },
    REJECTED: { cls: 'bg-rose-100 text-rose-800 border-rose-300', label: t ? t('rejected.verification') : 'Verification Rejected' },
    PENDING: { cls: 'bg-amber-100 text-amber-800 border-amber-300', label: t ? t('pending.verification') : 'Pending Verification' },
  }
  const config = configs[status] || configs.PENDING
  return (
    <motion.span
      className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${config.cls}`}
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{ type: 'spring', stiffness: 500, damping: 25 }}
    >
      {config.label}
    </motion.span>
  )
}
