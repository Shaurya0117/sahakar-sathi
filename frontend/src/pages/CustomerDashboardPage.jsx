import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import LocationPicker from '../components/LocationPicker'
import PortalHeader from '../components/PortalHeader'
import Footer from '../components/Footer'
import AnimatedPage from '../components/AnimatedPage'
import Modal from '../components/Modal'
import ServiceTimeline from '../components/ServiceTimeline'
import FloatingWhatsAppWidget from '../components/FloatingWhatsAppWidget'
import { PageSkeleton } from '../components/Skeleton'
import {
  MotionCard,
  MotionButton,
  ScrollReveal,
  staggerContainer,
  fadeInUp,
} from '../components/MotionPrimitives'
import { useAuth } from '../context/AuthContext'
import { getCustomerBookings } from '../services/bookingService'
import { getServices } from '../services/cooperativeService'
import {
  cancelServiceRequest,
  createServiceRequest,
  getMyServiceRequests,
  uploadServiceRequestPhoto,
} from '../services/requestService'
import { submitReview } from '../services/bookingService'
import toast from 'react-hot-toast'

export default function CustomerDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  // State
  const [services, setServices] = useState([])
  const [requests, setRequests] = useState([])
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Modals state
  const [selectedService, setSelectedService] = useState(null)
  const [selectedRequest, setSelectedRequest] = useState(null)
  const [reviewBooking, setReviewBooking] = useState(null)
  const [isCheckoutModalOpen, setIsCheckoutModalOpen] = useState(false)

  // Cart & Catalog state
  const [cart, setCart] = useState([])
  const [activeCategory, setActiveCategory] = useState('All')

  // Review Form fields
  const [rating, setRating] = useState(5)
  const [reviewText, setReviewText] = useState('')

  // Chat State
  const [chatBooking, setChatBooking] = useState(null)
  const [chatMessages, setChatMessages] = useState([
    { id: 1, sender: 'worker', text: 'Hello! I received your service request.', time: '10:00 AM' },
    { id: 2, sender: 'worker', text: 'I will be arriving at the scheduled time. Let me know if you have any specific instructions!', time: '10:01 AM' }
  ])
  const [newMessage, setNewMessage] = useState('')

  // Payment State
  const [paymentBooking, setPaymentBooking] = useState(null)
  const [paidBookings, setPaidBookings] = useState(() => {
    try { return JSON.parse(localStorage.getItem('paidBookings') || '[]') } catch { return [] }
  })
  const [processingPayment, setProcessingPayment] = useState(false)

  // AI Assistant State
  const [aiChatOpen, setAiChatOpen] = useState(false)
  const [aiMessages, setAiMessages] = useState([
    { role: 'ai', text: 'Hi! I am your Cooperative AI Assistant. Describe your problem, and I will find the right worker for you!' }
  ])
  const [aiChatInput, setAiChatInput] = useState('')
  const [isAiTyping, setIsAiTyping] = useState(false)

  // Request Form fields
  const [description, setDescription] = useState('')
  const [location, setLocation] = useState('')
  const [latitude, setLatitude] = useState(null)
  const [longitude, setLongitude] = useState(null)
  const [preferredDate, setPreferredDate] = useState('')
  const [preferredTime, setPreferredTime] = useState('10:00')
  const [photo, setPhoto] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [servicesRes, requestsRes, bookingsRes] = await Promise.all([
        getServices(),
        getMyServiceRequests(),
        getCustomerBookings(),
      ])
      setServices(servicesRes.data)
      setRequests(requestsRes.data)
      setBookings(bookingsRes.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load customer marketplace data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // openRequestModal removed as we now use Cart

  const handleAddToCart = (service) => {
    if (cart.find(item => item.id === service.id)) {
      toast.error(`${service.name} is already in your cart!`)
      return
    }
    setCart([...cart, service])
    toast.success(`${service.name} added to cart!`)
  }

  const handleRemoveFromCart = (serviceId) => {
    setCart(cart.filter(item => item.id !== serviceId))
  }

  const handleCheckout = () => {
    if (cart.length === 0) return
    setIsCheckoutModalOpen(true)
    setDescription('')
    setLocation(user?.location || 'Sector 62, Noida')
    setLatitude(null)
    setLongitude(null)
    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    setPreferredDate(tomorrow.toISOString().split('T')[0])
    setPreferredTime('10:00')
    setFormError('')
  }

  const handleSubmitCheckout = async (e) => {
    e.preventDefault()
    setFormError('')
    if (!location.trim()) {
      setFormError('Please provide your service location.')
      return
    }
    if (!preferredDate) {
      setFormError('Please select a preferred service date.')
      return
    }
    if (!preferredTime) {
      setFormError('Please select a preferred service time.')
      return
    }
    setSubmitting(true)
    try {
      const promises = cart.map(item => {
        const payload = {
          service_id: item.id,
          location: location.trim(),
          latitude, longitude,
          preferred_date: preferredDate,
          preferred_time: preferredTime,
          description: description.trim() || `Service request for ${item.name}`,
        }
        return createServiceRequest(payload)
      })

      const results = await Promise.all(promises)
      const newReqs = results.map(res => res.data)
      
      setRequests((prev) => [...newReqs, ...prev])
      setCart([])
      setIsCheckoutModalOpen(false)
      toast.success(`Successfully booked ${newReqs.length} services!`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit service requests.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancelRequest = async (requestId) => {
    try {
      const res = await cancelServiceRequest(requestId)
      const updatedReq = res.data.request
      setRequests((prev) => prev.map((r) => (r.id === requestId ? updatedReq : r)))
      if (selectedRequest?.id === requestId) setSelectedRequest(updatedReq)
      toast.success(`Service request #${requestId} cancelled successfully.`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to cancel request.')
    }
  }

  const handleSubmitReview = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const res = await submitReview(reviewBooking.id, rating, reviewText.trim())
      setBookings((prev) => prev.map((b) => (b.id === reviewBooking.id ? res.data : b)))
      setReviewBooking(null)
      toast.success('Thank you for your feedback! Review submitted.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit review.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSendMessage = (e) => {
    e.preventDefault()
    if (!newMessage.trim()) return
    const userMsg = {
      id: Date.now(), sender: 'customer', text: newMessage,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    setChatMessages((prev) => [...prev, userMsg])
    setNewMessage('')
    setTimeout(() => {
      setChatMessages((prev) => [...prev, {
        id: Date.now() + 1, sender: 'worker', text: 'Got it! See you soon. 👍',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    }, 1500)
  }

  const handleDownloadReceipt = (booking, request) => {
    const receiptContent = `
=========================================
      COOPERATIVE SERVICE RECEIPT
=========================================
Booking ID: ${booking.id}
Date: ${new Date(booking.created_at).toLocaleDateString()}
Status: COMPLETED

Customer Name: ${user?.name}
Customer Email: ${user?.email}

Worker Assigned: ${booking.worker_name}
Service Performed: ${request.service_name}
Location: ${request.location}
Service Date: ${booking.scheduled_date} at ${booking.scheduled_time}
Total Amount: $${booking.amount ? booking.amount.toFixed(2) : '0.00'}

Thank you for choosing the Cooperative!
=========================================
`
    const blob = new Blob([receiptContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Receipt_Booking_${booking.id}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    toast.success('Receipt downloaded successfully!')
  }

  const handleRebook = (request) => {
    const service = services.find(s => s.name === request.service_name)
    if (service) {
      if (!cart.find(c => c.id === service.id)) {
        setCart(prev => [...prev, service])
      }
      handleCheckout()
      setLocation(request.location)
      toast('Please review the details for your re-booking', { icon: '🔄' })
    } else {
      toast.error('Service no longer available in catalog')
    }
  }

  const handleProcessPayment = (e) => {
    e.preventDefault()
    setProcessingPayment(true)
    setTimeout(() => {
      const newPaid = [...paidBookings, paymentBooking.id]
      setPaidBookings(newPaid)
      localStorage.setItem('paidBookings', JSON.stringify(newPaid))
      setProcessingPayment(false)
      setPaymentBooking(null)
      toast.success('Payment processed successfully!')
    }, 2000)
  }

  const handleSendAiMessage = (e) => {
    e.preventDefault()
    if (!aiChatInput.trim()) return
    const userText = aiChatInput.trim()
    setAiMessages(prev => [...prev, { role: 'user', text: userText }])
    setAiChatInput('')
    setIsAiTyping(true)
    setTimeout(() => {
      const text = userText.toLowerCase()
      let matchedService = services[0]
      if (text.includes('leak') || text.includes('pipe') || text.includes('water') || text.includes('sink')) {
        matchedService = services.find(s => s.name.toLowerCase().includes('plumbing')) || services[0]
      } else if (text.includes('light') || text.includes('wire') || text.includes('switch') || text.includes('fan') || text.includes('electrical')) {
        matchedService = services.find(s => s.name.toLowerCase().includes('electrical')) || services[0]
      } else if (text.includes('clean') || text.includes('dust') || text.includes('mop') || text.includes('sweep')) {
        matchedService = services.find(s => s.name.toLowerCase().includes('cleaning')) || services[0]
      } else if (text.includes('ac') || text.includes('cool') || text.includes('fridge')) {
        matchedService = services.find(s => s.name.toLowerCase().includes('ac') || s.name.toLowerCase().includes('refrigeration')) || services[0]
      } else if (text.includes('wood') || text.includes('door') || text.includes('furniture')) {
        matchedService = services.find(s => s.name.toLowerCase().includes('carpentry')) || services[0]
      } else if (text.includes('paint') || text.includes('wall') || text.includes('color')) {
        matchedService = services.find(s => s.name.toLowerCase().includes('paint')) || services[0]
      }
      setAiMessages(prev => [...prev, {
        role: 'ai',
        text: `I can certainly help with that! It looks like you need assistance with "${matchedService.name}". I have pre-filled a service request for you.`
      }])
      setIsAiTyping(false)
      setTimeout(() => {
        setAiChatOpen(false)
        if (!cart.find(c => c.id === matchedService.id)) {
          setCart(prev => [...prev, matchedService])
        }
        setIsCheckoutModalOpen(true)
        setDescription(userText)
      }, 1500)
    }, 1800)
  }

  // Service category icons
  const categoryIcons = {
    'ELECTRICAL': '⚡', 'PLUMBING': '🔧', 'CLEANING': '🧹',
    'CARPENTRY': '🪚', 'PAINTING': '🎨', 'AC_SERVICING': '❄️',
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
        <PortalHeader />
        <PageSkeleton cards={6} />
      </div>
    )
  }

  return (
    <AnimatedPage className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <PortalHeader />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-8">

        {/* ── Welcome Header ─────────────────────────────────────── */}
        <motion.div
          className="relative bg-gradient-to-r from-blue-900 to-slate-900 p-8 rounded-2xl shadow-xl overflow-hidden flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 text-white"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <motion.div
            className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none text-8xl"
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          >
            🏡
          </motion.div>
          <div className="relative z-10">
            <motion.div
              className="flex items-center gap-2 mb-2"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              <span className="bg-blue-500/20 text-blue-200 font-bold text-[10px] px-2.5 py-1 rounded-full border border-blue-400/30 tracking-wider uppercase">
                Customer Marketplace
              </span>
            </motion.div>
            <motion.h1
              className="text-3xl font-extrabold mt-1 tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-blue-200"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              Welcome back, {user?.name}
            </motion.h1>
            <motion.p
              className="text-sm text-blue-200 mt-1"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              {user?.email}
            </motion.p>
          </div>

          <motion.div
            className="relative z-10 bg-white/10 backdrop-blur-md p-4 rounded-xl border border-white/20 text-sm w-full sm:w-auto"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            whileHover={{ scale: 1.02, borderColor: 'rgba(255,255,255,0.4)' }}
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-xl">📞</div>
              <div>
                <div className="text-blue-100 font-medium text-xs">24/7 Cooperative Support</div>
                <strong className="text-white text-lg tracking-wide">1800-266-7737</strong>
              </div>
            </div>
          </motion.div>
        </motion.div>

        {/* Banners */}
        <AnimatePresence>
          {error && (
            <motion.div
              className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <span>⚠️ {error}</span>
              <button onClick={() => setError(null)} className="text-rose-600 font-bold">✕</button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Cart Banner ────────────────────────────────────────── */}
        <AnimatePresence>
          {cart.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="sticky top-20 z-40 bg-white/90 backdrop-blur-md border border-blue-200 shadow-lg rounded-2xl p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="bg-blue-100 text-blue-700 w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg">
                  {cart.length}
                </div>
                <div>
                  <h3 className="font-bold text-slate-900">Services in Cart</h3>
                  <p className="text-xs text-slate-500 font-medium">Ready for checkout</p>
                </div>
              </div>
              <div className="flex gap-2">
                <MotionButton
                  onClick={() => setCart([])}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition"
                >
                  Clear
                </MotionButton>
                <MotionButton
                  onClick={handleCheckout}
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition shadow-md"
                >
                  Checkout Now
                </MotionButton>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Service Catalog Marketplace ────────────────────────── */}
        <section className="space-y-6 mt-8">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h2 className="text-2xl font-extrabold text-slate-900">Premium Home Services</h2>
              <p className="text-sm text-slate-500 font-medium">Book trusted professionals instantly</p>
            </div>
            
            {/* Category Pills */}
            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide max-w-full">
              {['All', ...new Set(services.map(s => s.category))].map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-4 py-2 rounded-full text-xs font-bold whitespace-nowrap transition-all shadow-sm ${
                    activeCategory === cat 
                      ? 'bg-slate-900 text-white' 
                      : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {(activeCategory === 'All' ? services : services.filter(s => s.category === activeCategory)).map(svc => (
              <motion.div
                key={svc.id}
                whileHover={{ y: -4 }}
                className="bg-white rounded-2xl overflow-hidden border border-slate-200 shadow-sm hover:shadow-xl transition-all flex flex-col group"
              >
                {/* Image Header */}
                <div className="h-40 bg-slate-100 relative overflow-hidden">
                  {svc.image_url ? (
                    <img src={svc.image_url} alt={svc.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-5xl bg-gradient-to-br from-blue-50 to-slate-100">
                      {svc.icon || '🛠️'}
                    </div>
                  )}
                  <div className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-lg text-[10px] font-bold text-slate-800 shadow-sm flex items-center gap-1">
                    <span className="text-amber-500">★</span> {svc.rating.toFixed(1)} <span className="text-slate-400 font-normal">({svc.reviews_count})</span>
                  </div>
                </div>

                {/* Content */}
                <div className="p-5 flex flex-col flex-1">
                  <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider mb-1">{svc.category}</span>
                  <h3 className="font-extrabold text-slate-900 text-lg leading-tight mb-2">{svc.name}</h3>
                  <p className="text-xs text-slate-500 line-clamp-2 mb-4 flex-1">{svc.description}</p>
                  
                  <div className="flex items-center justify-between pt-4 border-t border-slate-100 mt-auto">
                    <div>
                      <div className="font-extrabold text-slate-900">₹{svc.price}</div>
                      <div className="text-[10px] font-medium text-slate-500">{svc.duration_minutes} mins</div>
                    </div>
                    {cart.find(c => c.id === svc.id) ? (
                      <MotionButton
                        onClick={() => handleRemoveFromCart(svc.id)}
                        className="px-4 py-2 bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 text-xs font-bold rounded-xl transition shadow-sm"
                      >
                        Remove
                      </MotionButton>
                    ) : (
                      <MotionButton
                        onClick={() => handleAddToCart(svc)}
                        className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl transition shadow-sm"
                      >
                        Add to Cart
                      </MotionButton>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── My Service Requests ────────────────────────────────── */}
        <section id="requests" className="space-y-4 pt-4">
          <ScrollReveal>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">My Service Requests</h2>
                <p className="text-xs text-slate-500">Track status and inspect assigned worker details</p>
              </div>
              <span className="text-xs text-slate-500 font-medium">{requests.length} Requests Total</span>
            </div>
          </ScrollReveal>

          {requests.length === 0 ? (
            <motion.div
              className="bg-white p-10 text-center text-slate-500 border border-slate-200 rounded-2xl"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <motion.div
                className="text-4xl mb-3"
                animate={{ y: [0, -5, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                📋
              </motion.div>
              <p className="font-bold text-slate-800 text-sm">No service requests submitted yet</p>
              <p className="text-xs text-slate-500 mt-1">Select a service above to request worker allocation.</p>
            </motion.div>
          ) : (
            <motion.div
              className="grid grid-cols-1 md:grid-cols-2 gap-5"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {requests.map((req) => {
                const booking = bookings.find((b) => b.request_id === req.id && b.status !== 'REJECTED')
                return (
                  <motion.div
                    key={req.id}
                    variants={fadeInUp}
                    whileHover={{ y: -3 }}
                    className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow space-y-4"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-[10px] font-mono font-bold text-slate-400">Request #{req.id}</span>
                        <h3 className="text-base font-bold text-slate-900">{req.service_name}</h3>
                        <p className="text-xs text-slate-500">{req.service_category}</p>
                      </div>
                      <RequestStatusBadge status={req.status} bookingStatus={booking?.status} />
                    </div>

                    {/* Service Timeline */}
                    <ServiceTimeline
                      requestStatus={req.status}
                      bookingStatus={booking?.status}
                      createdAt={req.created_at}
                    />

                    {/* Worker Assignment */}
                    <AnimatePresence>
                      {booking && (
                        <motion.div
                          className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs flex items-center justify-between"
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                        >
                          <div>
                            <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">Assigned Cooperative Member</p>
                            <p className="font-bold text-slate-900">{booking.worker_name}</p>
                          </div>
                          <span className="text-[11px] font-bold text-emerald-800 bg-white px-2.5 py-1 rounded-lg border border-emerald-300">
                            {booking.status === 'ASSIGNED' ? 'Assigned' : booking.status === 'ACCEPTED' ? 'Accepted' : booking.status === 'IN_PROGRESS' ? 'In Progress' : 'Completed'}
                          </span>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Details */}
                    <div className="space-y-1.5 text-xs text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-200">
                      <p className="flex items-center gap-2"><span className="text-slate-400">📍</span><strong>Location:</strong> {req.location}</p>
                      <p className="flex items-center gap-2"><span className="text-slate-400">📅</span><strong>Scheduled:</strong> {req.preferred_date} • {req.preferred_time}</p>
                      <p className="text-slate-600 italic pt-1">"{req.description}"</p>
                    </div>

                    {/* Actions */}
                    <div className="flex flex-col gap-2 pt-2 border-t border-slate-100">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <MotionButton
                          onClick={() => setSelectedRequest(req)}
                          className="text-xs font-bold text-blue-700 hover:underline"
                        >
                          View Request Details →
                        </MotionButton>

                        {req.status === 'PENDING' && (
                          <MotionButton
                            onClick={() => handleCancelRequest(req.id)}
                            className="px-3 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold rounded-lg transition"
                          >
                            Cancel Request
                          </MotionButton>
                        )}

                        {booking && ['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'].includes(booking.status) && (
                          <MotionButton
                            onClick={() => setChatBooking(booking)}
                            className="px-3 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-bold rounded-lg transition flex items-center gap-1"
                          >
                            <span>💬</span> Message Worker
                          </MotionButton>
                        )}

                        {booking?.status === 'COMPLETED' && (
                          <div className="flex gap-2 flex-wrap">
                            {!paidBookings.includes(booking.id) && booking.amount > 0 && (
                              <MotionButton
                                onClick={() => setPaymentBooking(booking)}
                                className="px-2 py-1 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition flex items-center gap-1 shadow-sm"
                              >
                                💳 Pay ${booking.amount}
                              </MotionButton>
                            )}
                            {paidBookings.includes(booking.id) && (
                              <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold rounded-lg flex items-center gap-1">
                                ✓ Paid
                              </span>
                            )}
                            <MotionButton
                              onClick={() => handleDownloadReceipt(booking, req)}
                              className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 text-xs font-bold rounded-lg transition flex items-center gap-1"
                            >
                              🧾 Receipt
                            </MotionButton>
                            <MotionButton
                              onClick={() => handleRebook(req)}
                              className="px-2 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-xs font-bold rounded-lg transition flex items-center gap-1"
                            >
                              🔄 Re-book
                            </MotionButton>
                          </div>
                        )}
                      </div>

                      {booking?.status === 'COMPLETED' && !booking.customer_rating && (
                        <MotionButton
                          onClick={() => {
                            setReviewBooking(booking)
                            setRating(5)
                            setReviewText('')
                          }}
                          className="w-full mt-2 py-2 bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white text-xs font-bold rounded-xl transition shadow-sm"
                        >
                          Leave a Review ⭐
                        </MotionButton>
                      )}

                      {booking?.customer_rating && (
                        <motion.div
                          className="mt-2 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                        >
                          <div className="text-amber-500 font-bold mb-1">
                            {'★'.repeat(booking.customer_rating)}{'☆'.repeat(5 - booking.customer_rating)}
                          </div>
                          {booking.customer_review && <p className="text-slate-600 italic">"{booking.customer_review}"</p>}
                        </motion.div>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </motion.div>
          )}
        </section>
      </main>

      {/* ── Checkout Modal ─────────────────────────────────────── */}
      <Modal
        isOpen={isCheckoutModalOpen}
        onClose={() => setIsCheckoutModalOpen(false)}
        title="Checkout Services"
        subtitle="Schedule and confirm your selected services"
      >
        <div className="mb-4 p-3 bg-blue-50 border border-blue-100 rounded-xl max-h-32 overflow-y-auto">
          <p className="text-[10px] font-bold text-blue-800 uppercase tracking-wider mb-2">Order Summary</p>
          {cart.map(item => (
            <div key={item.id} className="flex items-center justify-between text-xs text-slate-700 mb-1">
              <span>{item.name}</span>
              <span className="font-bold">₹{item.price}</span>
            </div>
          ))}
          <div className="flex items-center justify-between text-xs font-bold text-slate-900 pt-2 mt-2 border-t border-blue-200">
            <span>Total estimated price:</span>
            <span>₹{cart.reduce((sum, item) => sum + item.price, 0)}</span>
          </div>
        </div>

        {formError && (
          <motion.div
            className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs mt-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            ⚠️ {formError}
          </motion.div>
        )}

        <form onSubmit={handleSubmitCheckout} className="space-y-4 mt-2">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Additional Instructions (Optional)
            </label>
            <textarea
              rows={2} value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Any specific requests for the professionals..."
              className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-xl text-slate-900 text-xs focus:ring-2 focus:ring-blue-600 outline-none transition"
            />
          </div>
          <LocationPicker
            required locationValue={location} latitudeValue={latitude} longitudeValue={longitude}
            onChange={({ location: loc, latitude: lat, longitude: lon }) => {
              setLocation(loc); setLatitude(lat); setLongitude(lon)
            }}
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Preferred Date <span className="text-rose-600">*</span></label>
              <input type="date" required value={preferredDate} onChange={(e) => setPreferredDate(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-slate-900 text-xs outline-none" />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Preferred Time <span className="text-rose-600">*</span></label>
              <select value={preferredTime} onChange={(e) => setPreferredTime(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-slate-900 text-xs outline-none">
                <option value="09:00">9:00 AM</option>
                <option value="10:00">10:00 AM</option>
                <option value="11:00">11:00 AM</option>
                <option value="12:00">12:00 PM</option>
                <option value="14:00">2:00 PM</option>
                <option value="15:00">3:00 PM</option>
                <option value="16:00">4:00 PM</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-3 border-t border-slate-200">
            <MotionButton type="submit" disabled={submitting}
              className="flex-1 py-2.5 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-blue-700 text-xs transition disabled:opacity-50 shadow-sm">
              {submitting ? 'Processing...' : 'Confirm Booking'}
            </MotionButton>
            <MotionButton type="button" onClick={() => setIsCheckoutModalOpen(false)}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-xl transition">
              Cancel
            </MotionButton>
          </div>
        </form>
      </Modal>

      {/* ── Request Detail Modal ───────────────────────────────── */}
      <Modal isOpen={!!selectedRequest} onClose={() => setSelectedRequest(null)}>
        {selectedRequest && (
          <>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-mono text-slate-400">Request #{selectedRequest.id}</span>
              <RequestStatusBadge status={selectedRequest.status} />
            </div>
            <h2 className="text-xl font-bold text-slate-900">{selectedRequest.service_name}</h2>
            <p className="text-xs text-slate-500 mb-4">{selectedRequest.service_category}</p>

            <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
              <div><p className="text-slate-500 font-bold uppercase text-[10px]">Task Description</p><p className="text-slate-800 mt-1">{selectedRequest.description}</p></div>
              {selectedRequest.image_url && (
                <div className="pt-2"><p className="text-slate-500 font-bold uppercase text-[10px] mb-1">Attached Photo</p>
                  <img src={`http://localhost:8000${selectedRequest.image_url}`} alt="Attached issue" className="max-h-48 rounded-xl border border-slate-200 object-cover" />
                </div>
              )}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200">
                <div><p className="text-slate-500 font-bold uppercase text-[10px]">Location</p><p className="text-slate-800 mt-0.5">📍 {selectedRequest.location}</p></div>
                <div><p className="text-slate-500 font-bold uppercase text-[10px]">Scheduled</p><p className="text-slate-800 mt-0.5">📅 {selectedRequest.preferred_date} • {selectedRequest.preferred_time}</p></div>
              </div>
            </div>

            {selectedRequest.status === 'PENDING' && (
              <MotionButton onClick={() => handleCancelRequest(selectedRequest.id)}
                className="w-full mt-4 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold rounded-xl transition">
                Cancel Service Request
              </MotionButton>
            )}
          </>
        )}
      </Modal>

      {/* ── Review Modal ───────────────────────────────────────── */}
      <Modal isOpen={!!reviewBooking} onClose={() => setReviewBooking(null)} title="Rate Your Service"
        subtitle={reviewBooking ? `How was your experience with ${reviewBooking.worker_name}?` : ''} maxWidth="max-w-md">
        {reviewBooking && (
          <form onSubmit={handleSubmitReview} className="space-y-4 mt-2">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-2">Rating (1-5)</label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((num) => (
                  <motion.button key={num} type="button" onClick={() => setRating(num)}
                    className={`w-10 h-10 rounded-full font-bold text-lg transition-all ${rating >= num ? 'bg-amber-100 text-amber-500 border-2 border-amber-300 shadow-sm' : 'bg-slate-100 text-slate-400 border-2 border-slate-200'}`}
                    whileHover={{ scale: 1.15 }} whileTap={{ scale: 0.9 }}>★</motion.button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Write a Review (Optional)</label>
              <textarea rows={3} value={reviewText} onChange={(e) => setReviewText(e.target.value)} placeholder="Tell us what you liked..."
                className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-xl text-slate-900 text-xs focus:ring-2 focus:ring-blue-600 outline-none" />
            </div>
            <MotionButton type="submit" disabled={submitting}
              className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white text-xs font-bold rounded-xl transition disabled:opacity-50 shadow-sm">
              {submitting ? 'Submitting...' : 'Submit Review'}
            </MotionButton>
          </form>
        )}
      </Modal>

      {/* ── Chat Modal ─────────────────────────────────────────── */}
      <AnimatePresence>
        {chatBooking && (
          <motion.div className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setChatBooking(null)} />
            <motion.div className="bg-slate-50 rounded-2xl border border-slate-200 shadow-2xl max-w-sm w-full flex flex-col overflow-hidden relative z-10"
              style={{ height: '500px' }}
              initial={{ opacity: 0, scale: 0.9, y: 30 }} animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 30 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}>
              <div className="bg-gradient-to-r from-slate-800 to-slate-900 text-white p-4 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm">👷</div>
                  <div>
                    <h3 className="text-sm font-bold">{chatBooking.worker_name}</h3>
                    <p className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                      <motion.span className="w-1.5 h-1.5 rounded-full bg-emerald-400" animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
                      Online
                    </p>
                  </div>
                </div>
                <MotionButton onClick={() => setChatBooking(null)} variant="icon" className="text-slate-400 hover:text-white">✕</MotionButton>
              </div>
              <div className="flex-1 p-4 overflow-y-auto space-y-4">
                <div className="text-center text-[10px] text-slate-400 my-2">Today</div>
                {chatMessages.map((msg, i) => (
                  <motion.div key={msg.id} className={`flex flex-col ${msg.sender === 'customer' ? 'items-end' : 'items-start'}`}
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                    <div className={`px-3 py-2 rounded-2xl max-w-[80%] text-xs shadow-sm ${msg.sender === 'customer' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'}`}>
                      {msg.text}
                    </div>
                    <span className="text-[9px] text-slate-400 mt-1 mx-1">{msg.time}</span>
                  </motion.div>
                ))}
              </div>
              <div className="p-3 bg-white border-t border-slate-200 shrink-0">
                <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                  <input type="text" value={newMessage} onChange={(e) => setNewMessage(e.target.value)} placeholder="Type a message..."
                    className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-full text-xs outline-none focus:border-blue-500 focus:bg-white transition" />
                  <MotionButton type="submit" disabled={!newMessage.trim()} variant="icon"
                    className="w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center transition disabled:opacity-50">
                    <span className="text-xs">➤</span>
                  </MotionButton>
                </form>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Payment Modal ──────────────────────────────────────── */}
      <Modal isOpen={!!paymentBooking} onClose={() => setPaymentBooking(null)} maxWidth="max-w-sm">
        {paymentBooking && (
          <>
            <div className="text-center">
              <motion.div className="w-14 h-14 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center text-2xl mx-auto mb-3"
                initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 400, damping: 20 }}>💳</motion.div>
              <h2 className="text-xl font-bold text-slate-900">Secure Payment</h2>
              <p className="text-xs text-slate-500 mt-1">Complete your payment for Booking #{paymentBooking.id}</p>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-center mt-4">
              <span className="text-xs font-bold text-slate-500 uppercase">Amount Due</span>
              <div className="text-3xl font-extrabold text-slate-900 mt-1">${paymentBooking.amount}</div>
            </div>
            <form onSubmit={handleProcessPayment} className="space-y-4 mt-4">
              <div><label className="block text-xs font-bold text-slate-700 mb-1">Card Number</label>
                <input type="text" required defaultValue="4242 4242 4242 4242"
                  className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none" /></div>
              <div className="flex gap-3">
                <div className="flex-1"><label className="block text-xs font-bold text-slate-700 mb-1">MM/YY</label>
                  <input type="text" required defaultValue="12/28" className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none" /></div>
                <div className="flex-1"><label className="block text-xs font-bold text-slate-700 mb-1">CVC</label>
                  <input type="text" required defaultValue="123" className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none" /></div>
              </div>
              <MotionButton type="submit" disabled={processingPayment}
                className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition shadow-md disabled:opacity-70">
                {processingPayment ? (
                  <><motion.div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full" animate={{ rotate: 360 }}
                    transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }} />Processing...</>
                ) : `Pay $${paymentBooking.amount}`}
              </MotionButton>
            </form>
          </>
        )}
      </Modal>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <Footer />

      {/* ── Floating AI Assistant ──────────────────────────────── */}
      <div className="fixed bottom-6 right-24 z-40">
        <AnimatePresence>
          {aiChatOpen && (
            <motion.div className="absolute bottom-16 right-0 w-[350px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden"
              initial={{ opacity: 0, y: 20, scale: 0.9 }} animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}>
              <div className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <motion.div className="text-2xl" animate={{ rotate: [0, 10, -10, 0] }} transition={{ duration: 2, repeat: Infinity }}>🤖</motion.div>
                  <div><div className="font-bold text-sm leading-tight">Sahakar Sathi AI</div><div className="text-[10px] text-blue-200">Smart Booking Assistant</div></div>
                </div>
                <MotionButton variant="icon" onClick={() => setAiChatOpen(false)} className="text-blue-200 hover:text-white">✕</MotionButton>
              </div>
              <div className="h-[300px] overflow-y-auto p-4 space-y-4 bg-slate-50">
                {aiMessages.map((msg, i) => (
                  <motion.div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                    <div className={`max-w-[85%] p-3 rounded-2xl text-xs shadow-sm ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'}`}>
                      {msg.text}
                    </div>
                  </motion.div>
                ))}
                {isAiTyping && (
                  <div className="flex justify-start">
                    <div className="bg-white text-slate-800 border border-slate-200 p-3 rounded-2xl rounded-tl-none text-xs flex gap-1 shadow-sm">
                      <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0 }}>●</motion.span>
                      <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0.2 }}>●</motion.span>
                      <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 0.8, repeat: Infinity, delay: 0.4 }}>●</motion.span>
                    </div>
                  </div>
                )}
              </div>
              <div className="p-3 bg-white border-t border-slate-200">
                <form onSubmit={handleSendAiMessage} className="flex gap-2">
                  <input type="text" value={aiChatInput} onChange={(e) => setAiChatInput(e.target.value)} placeholder="Describe your problem..."
                    className="flex-1 px-3 py-2 bg-slate-100 border border-transparent focus:border-blue-300 focus:bg-white rounded-full text-xs outline-none transition" disabled={isAiTyping} />
                  <MotionButton type="submit" variant="icon" disabled={!aiChatInput.trim() || isAiTyping}
                    className="w-8 h-8 bg-blue-600 hover:bg-blue-700 text-white rounded-full flex items-center justify-center disabled:opacity-50 transition">
                    <span className="text-xs">➤</span>
                  </MotionButton>
                </form>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.button
          onClick={() => setAiChatOpen(!aiChatOpen)}
          className={`w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition group ${aiChatOpen ? 'bg-slate-800 text-white' : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'}`}
          whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
          animate={!aiChatOpen ? { y: [0, -5, 0] } : {}}
          transition={!aiChatOpen ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : {}}
        >
          <span className="text-2xl">{aiChatOpen ? '✕' : '🤖'}</span>
          {!aiChatOpen && (
            <div className="absolute right-full mr-4 bg-slate-900 text-white text-[10px] font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition pointer-events-none whitespace-nowrap">
              Ask AI Assistant
            </div>
          )}
        </motion.button>
      </div>

      {/* ── Floating WhatsApp Widget ──────────────────────────────────── */}
      <FloatingWhatsAppWidget phoneNumber="919999999999" companyName="Sahakar Sathi Support" />
    </AnimatedPage>
  )
}

/** Status Badge for Service Requests */
function RequestStatusBadge({ status, bookingStatus }) {
  const displayStatus = bookingStatus || status
  const configs = {
    ASSIGNED: { cls: 'bg-blue-100 text-blue-800 border-blue-300', label: '📌 Assigned' },
    ACCEPTED: { cls: 'bg-emerald-100 text-emerald-800 border-emerald-300', label: '✓ Accepted' },
    IN_PROGRESS: { cls: 'bg-indigo-100 text-indigo-800 border-indigo-300', label: '⚙ In Progress' },
    COMPLETED: { cls: 'bg-emerald-100 text-emerald-900 border-emerald-400', label: '✓ Completed' },
    CANCELLED: { cls: 'bg-slate-100 text-slate-700 border-slate-300', label: '✕ Cancelled' },
    PENDING: { cls: 'bg-amber-100 text-amber-800 border-amber-300', label: '⏳ Pending' },
  }
  const config = configs[displayStatus] || configs.PENDING
  return (
    <motion.span
      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${config.cls}`}
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{ type: 'spring', stiffness: 500, damping: 25 }}
    >
      {config.label}
    </motion.span>
  )
}
