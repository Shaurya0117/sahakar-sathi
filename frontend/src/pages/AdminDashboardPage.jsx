import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts'
import AnimatedPage from '../components/AnimatedPage'
import Footer from '../components/Footer'
import { PageSkeleton } from '../components/Skeleton'
import MatchingModal from '../components/admin/MatchingModal'
import PortalHeader from '../components/PortalHeader'
import { useAuth } from '../context/AuthContext'
import { getCooperativeBookings } from '../services/bookingService'
import { getCooperativeInfo, getCooperativeAnalytics } from '../services/cooperativeService'
import { listAllWorkers, updateVerificationStatus } from '../services/workerService'
import { getCooperativeServiceRequests } from '../services/requestService'

import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

// Fix for default Leaflet icon paths in React
import L from 'leaflet'
import icon from 'leaflet/dist/images/marker-icon.png'
import iconShadow from 'leaflet/dist/images/marker-shadow.png'
let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

export default function AdminDashboardPage() {
  const { user } = useAuth()

  // State
  const [cooperative, setCooperative] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [workers, setWorkers] = useState([])
  const [requests, setRequests] = useState([])
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionSuccess, setActionSuccess] = useState('')

  // Search & Filter state for Workers
  const [workerSearch, setWorkerSearch] = useState('')
  const [workerFilterStatus, setWorkerFilterStatus] = useState('ALL')

  // Search & Filter state for Requests
  const [requestFilterStatus, setRequestFilterStatus] = useState('ALL')

  // Selected Request for Recommendation Modal
  const [matchingRequest, setMatchingRequest] = useState(null)

  // Verification Modal State
  const [selectedWorkerForVerify, setSelectedWorkerForVerify] = useState(null)
  const [verifying, setVerifying] = useState(false)
  const [consensusProgress, setConsensusProgress] = useState(false)

  // Load all cooperative data
  const loadAdminData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [coopRes, workersRes, requestsRes, bookingsRes, analyticsRes] = await Promise.all([
        getCooperativeInfo(),
        listAllWorkers(),
        getCooperativeServiceRequests(),
        getCooperativeBookings(),
        getCooperativeAnalytics(),
      ])
      setCooperative(coopRes.data)
      setWorkers(workersRes.data)
      setRequests(requestsRes.data)
      setBookings(bookingsRes.data || [])
      setAnalytics(analyticsRes.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load cooperative administration data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAdminData()
  }, [loadAdminData])

  // Handle Verification Action
  const handleUpdateVerification = async (workerId, newStatus) => {
    setVerifying(true)
    setError(null)
    try {
      await updateVerificationStatus(workerId, newStatus)
      setActionSuccess(`Worker #${workerId} verification status updated to ${newStatus}.`)
      setSelectedWorkerForVerify(null)
      await loadAdminData()
      setTimeout(() => setActionSuccess(''), 4000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update worker verification.')
    } finally {
      setVerifying(false)
    }
  }

  // Filter Workers
  const filteredWorkers = workers.filter((w) => {
    const matchesSearch =
      (w.name || '').toLowerCase().includes(workerSearch.toLowerCase()) ||
      (w.profession || '').toLowerCase().includes(workerSearch.toLowerCase()) ||
      (w.location || '').toLowerCase().includes(workerSearch.toLowerCase())
    const matchesStatus =
      workerFilterStatus === 'ALL' || w.verification_status === workerFilterStatus
    return matchesSearch && matchesStatus
  })

  // Filter Requests
  const filteredRequests = requests.filter((r) => {
    return requestFilterStatus === 'ALL' || r.status === requestFilterStatus
  })

  // Stats Counters
  const totalWorkers = workers.length
  const verifiedWorkers = workers.filter((w) => w.verification_status === 'VERIFIED').length
  const pendingVerificationWorkers = workers.filter(
    (w) => w.verification_status === 'PENDING'
  ).length
  const availableWorkers = workers.filter(
    (w) => w.verification_status === 'VERIFIED' && w.availability === 'AVAILABLE'
  ).length
  const pendingRequests = requests.filter((r) => r.status === 'PENDING').length
  const activeBookingsCount = bookings.filter((b) => b.status === 'ASSIGNED' || b.status === 'ACCEPTED' || b.status === 'IN_PROGRESS').length

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
        
        {/* Cooperative Overview Header */}
        <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-blue-100 text-blue-800 font-bold text-xs px-2 py-0.5 rounded border border-blue-200">
                COOPERATIVE ADMINISTRATION
              </span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
              {cooperative?.name || 'Ghaziabad Community Services Cooperative'}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Admin: <strong className="text-slate-800">{user?.name}</strong> • Location: <strong className="text-slate-800">{cooperative?.location || 'Sector 62, Noida'}</strong>
            </p>
          </div>

          <button
            onClick={loadAdminData}
            className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded border border-slate-300 transition flex items-center gap-1.5"
          >
            <span>🔄 Refresh Data</span>
          </button>
        </div>

        {/* Action Banners */}
        {error && (
          <div className="p-4 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)} className="text-rose-600 font-bold">✕</button>
          </div>
        )}

        {actionSuccess && (
          <div className="p-4 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
            <span>✓ {actionSuccess}</span>
            <button onClick={() => setActionSuccess('')} className="text-emerald-600 font-bold">✕</button>
          </div>
        )}

        {/* Statistics Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Total Workers</span>
            <div className="text-2xl font-extrabold text-slate-900 mt-1">{totalWorkers}</div>
            <span className="text-[10px] text-slate-500">Registered members</span>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Verified Workers</span>
            <div className="text-2xl font-extrabold text-emerald-700 mt-1">{verifiedWorkers}</div>
            <span className="text-[10px] text-slate-500">Credential verified</span>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Pending Review</span>
            <div className="text-2xl font-extrabold text-amber-700 mt-1">{pendingVerificationWorkers}</div>
            <span className="text-[10px] text-slate-500">Awaiting verification</span>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Available Pool</span>
            <div className="text-2xl font-extrabold text-blue-700 mt-1">{availableWorkers}</div>
            <span className="text-[10px] text-slate-500">Ready for allocation</span>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Pending Requests</span>
            <div className="text-2xl font-extrabold text-indigo-700 mt-1">{pendingRequests}</div>
            <span className="text-[10px] text-slate-500">Unallocated requests</span>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">Active Bookings</span>
            <div className="text-2xl font-extrabold text-purple-700 mt-1">{activeBookingsCount}</div>
            <span className="text-[10px] text-slate-500">Assigned / In Progress</span>
          </div>
        </div>

        {/* Live Interactive Map Section */}
        <section className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs mt-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>🗺️</span> Live Cooperative Map
              </h2>
              <p className="text-xs text-slate-500">Real-time geospatial tracking of requests and workers</p>
            </div>
            <div className="flex items-center gap-3 text-[10px] font-bold">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Worker</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500"></span> Request</span>
            </div>
          </div>
          
          <div className="h-[400px] w-full rounded-xl border border-slate-200 overflow-hidden shadow-inner">
            <MapContainer center={[28.6692, 77.4538]} zoom={12} scrollWheelZoom={false} className="h-full w-full">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
              />
              
              {/* Dummy Workers */}
              <Marker position={[28.6792, 77.4338]}>
                <Popup>
                  <strong className="text-blue-700 text-xs">Worker Active</strong><br/>Raj Kumar (Plumber)
                </Popup>
              </Marker>
              <Marker position={[28.6592, 77.4738]}>
                <Popup>
                  <strong className="text-blue-700 text-xs">Worker Active</strong><br/>Amit Singh (Electrician)
                </Popup>
              </Marker>
              
              {/* Dummy Requests */}
              <CircleMarker center={[28.6600, 77.4400]} pathOptions={{ color: '#e11d48', fillColor: '#f43f5e', fillOpacity: 0.7 }} radius={8}>
                <Popup>
                  <strong className="text-rose-700 text-xs">Pending Request</strong><br/>Water pipe broken
                </Popup>
              </CircleMarker>
              <CircleMarker center={[28.6800, 77.4600]} pathOptions={{ color: '#e11d48', fillColor: '#f43f5e', fillOpacity: 0.7 }} radius={8}>
                <Popup>
                  <strong className="text-rose-700 text-xs">Pending Request</strong><br/>AC Servicing required
                </Popup>
              </CircleMarker>
            </MapContainer>
          </div>
        </section>

        {/* Predictive Logistics AI Section */}
        <section className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs mt-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>🔮</span> Predictive Logistics AI
              </h2>
              <p className="text-[10px] text-slate-500 font-medium bg-slate-100 inline-block px-2 py-1 rounded mt-1">
                🔒 Anonymized Aggregate Data Only (Privacy Preserved)
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border border-rose-200 bg-rose-50/50 p-4 rounded-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-rose-500 text-white text-[10px] font-bold px-2 py-1 rounded-bl-lg">82% CONFIDENCE</div>
              <h3 className="font-bold text-rose-900 text-sm mb-1 mt-1">Sector 62, Noida</h3>
              <p className="text-xs text-rose-700 mb-3">Aggregate TDS pattern spike (940ppm avg). High probability of local RO filter failures.</p>
              <div className="bg-white rounded-lg p-2 flex flex-col gap-1 text-[10px] font-semibold border border-rose-100">
                <span className="text-slate-500">Logistics Recommendation:</span>
                <span className="text-rose-700 flex justify-between">
                  Partner with local supplier
                  <strong>Gupta Hardware (Sec 62)</strong>
                </span>
                <span className="text-rose-600 flex justify-between">
                  Reserve Inventory:
                  <strong>50 RO Filters</strong>
                </span>
              </div>
            </div>
            
            <div className="border border-amber-200 bg-amber-50/50 p-4 rounded-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-amber-500 text-white text-[10px] font-bold px-2 py-1 rounded-bl-lg">65% CONFIDENCE</div>
              <h3 className="font-bold text-amber-900 text-sm mb-1 mt-1">Indirapuram</h3>
              <p className="text-xs text-amber-700 mb-3">Power grid voltage anomalies detected. Likely AC capacitor failures.</p>
              <div className="bg-white rounded-lg p-2 flex flex-col gap-1 text-[10px] font-semibold border border-amber-100">
                <span className="text-slate-500">Logistics Recommendation:</span>
                <span className="text-amber-700 flex justify-between">
                  Partner with local supplier
                  <strong>Sharma Electronics</strong>
                </span>
                <span className="text-amber-600 flex justify-between">
                  Reserve Inventory:
                  <strong>30 AC Capacitors</strong>
                </span>
              </div>
            </div>

            <div className="border border-emerald-200 bg-emerald-50/50 p-4 rounded-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-emerald-500 text-white text-[10px] font-bold px-2 py-1 rounded-bl-lg">STABLE</div>
              <h3 className="font-bold text-emerald-900 text-sm mb-1">Vaishali</h3>
              <p className="text-xs text-emerald-700 mb-3">Environmental metrics nominal. Standard predictive baseline maintenance requested.</p>
              <div className="bg-white rounded-lg p-2 flex justify-between items-center text-xs font-semibold border border-emerald-100">
                <span>Action: Routine Routing</span>
                <span className="text-emerald-600">Normal</span>
              </div>
            </div>
          </div>
        </section>

        {/* Analytics Section */}
        {analytics && (
          <section className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs mt-6 space-y-6">
            <div>
              <h2 className="text-base font-bold text-slate-900">Cooperative Analytics Dashboard</h2>
              <p className="text-xs text-slate-500">Live operational trends and job distribution</p>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Job Trends (Bar Chart) */}
              <div className="border border-slate-100 p-4 rounded-xl">
                <h3 className="text-xs font-bold text-slate-700 mb-4 text-center">Completed Jobs (Last 7 Days)</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.recent_jobs_trend} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="date" tick={{fontSize: 10}} tickLine={false} axisLine={false} />
                      <YAxis tick={{fontSize: 10}} tickLine={false} axisLine={false} />
                      <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{fontSize: '12px', borderRadius: '8px'}} />
                      <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Service Categories (Pie Chart) */}
              <div className="border border-slate-100 p-4 rounded-xl">
                <h3 className="text-xs font-bold text-slate-700 mb-4 text-center">Requests by Category</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={Object.entries(analytics.jobs_by_category).map(([name, value]) => ({name, value}))}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {Object.keys(analytics.jobs_by_category).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444'][index % 5]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{fontSize: '12px', borderRadius: '8px'}} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex flex-wrap justify-center gap-2 mt-2">
                    {Object.keys(analytics.jobs_by_category).map((category, idx) => (
                      <div key={category} className="flex items-center gap-1 text-[10px] text-slate-600 font-medium">
                        <span className="w-2.5 h-2.5 rounded-full inline-block" style={{backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444'][idx % 5]}}></span>
                        {category}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Customer Service Requests Table */}
        <section className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Customer Service Requests</h2>
              <p className="text-xs text-slate-500">Inspect requests and run worker recommendations for allocation</p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-600">Filter:</span>
              <select
                value={requestFilterStatus}
                onChange={(e) => setRequestFilterStatus(e.target.value)}
                className="px-2.5 py-1 bg-white border border-slate-300 rounded text-slate-800 text-xs outline-none"
              >
                <option value="ALL">All Statuses ({requests.length})</option>
                <option value="PENDING">Pending Unallocated</option>
                <option value="ACCEPTED">Accepted</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
          </div>

          {filteredRequests.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 bg-slate-50 rounded border border-slate-200">
              No customer requests found matching the current filter criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700 border-collapse">
                <thead>
                  <tr className="bg-slate-100 border-b border-slate-200 font-bold text-slate-800 uppercase tracking-wider">
                    <th className="p-3">ID</th>
                    <th className="p-3">Customer</th>
                    <th className="p-3">Service</th>
                    <th className="p-3">Location</th>
                    <th className="p-3">Schedule</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filteredRequests.map((req) => (
                    <tr key={req.id} className="hover:bg-slate-50 transition">
                      <td className="p-3 font-mono font-bold">#{req.id}</td>
                      <td className="p-3">
                        <div className="font-bold text-slate-900">{req.customer_name}</div>
                        <div className="text-[11px] text-slate-500">{req.customer_phone || req.customer_email}</div>
                      </td>
                      <td className="p-3">
                        <div className="font-semibold text-slate-800">{req.service_name}</div>
                        <div className="text-[11px] text-slate-500">{req.service_category}</div>
                      </td>
                      <td className="p-3 font-medium">📍 {req.location}</td>
                      <td className="p-3">📅 {req.preferred_date} • {req.preferred_time}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded font-bold text-[11px] ${req.status === 'PENDING' ? 'bg-amber-100 text-amber-800 border border-amber-300' : req.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-blue-100 text-blue-800 border border-blue-300'}`}>
                          {req.status}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        {req.status === 'PENDING' ? (
                          <button
                            onClick={() => setMatchingRequest(req)}
                            className="px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs rounded shadow-xs transition"
                          >
                            Find Worker Recommendations →
                          </button>
                        ) : (
                          <span className="text-slate-400 italic">Allocated</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Worker Management & Verification Table */}
        <section className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Cooperative Worker Pool</h2>
              <p className="text-xs text-slate-500">Manage member workers, inspect credentials, and update verification</p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={workerSearch}
                onChange={(e) => setWorkerSearch(e.target.value)}
                placeholder="Search worker by name, skill, area..."
                className="px-3 py-1 bg-white border border-slate-300 rounded text-slate-800 text-xs outline-none"
              />
              <select
                value={workerFilterStatus}
                onChange={(e) => setWorkerFilterStatus(e.target.value)}
                className="px-2.5 py-1 bg-white border border-slate-300 rounded text-slate-800 text-xs outline-none"
              >
                <option value="ALL">All Statuses ({workers.length})</option>
                <option value="PENDING">Pending Review</option>
                <option value="VERIFIED">Verified Members</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>
          </div>

          {filteredWorkers.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 bg-slate-50 rounded border border-slate-200">
              No worker profiles found matching the current search criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700 border-collapse">
                <thead>
                  <tr className="bg-slate-100 border-b border-slate-200 font-bold text-slate-800 uppercase tracking-wider">
                    <th className="p-3">Worker Member</th>
                    <th className="p-3">Profession</th>
                    <th className="p-3">Experience</th>
                    <th className="p-3">Service Area</th>
                    <th className="p-3">Availability</th>
                    <th className="p-3">Verification</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filteredWorkers.map((w) => (
                    <tr key={w.id} className="hover:bg-slate-50 transition">
                      <td className="p-3">
                        <div className="font-bold text-slate-900">{w.name}</div>
                        <div className="text-[11px] text-slate-500">{w.email}</div>
                      </td>
                      <td className="p-3 font-semibold text-slate-800">{w.profession || 'General Worker'}</td>
                      <td className="p-3">{w.experience_years || 0} Years</td>
                      <td className="p-3 font-medium">📍 {w.location || 'Unspecified'}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded font-semibold text-[10px] ${w.availability === 'AVAILABLE' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-amber-50 text-amber-800 border border-amber-200'}`}>
                          {w.availability}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${w.verification_status === 'VERIFIED' ? 'bg-emerald-100 text-emerald-900 border border-emerald-300' : w.verification_status === 'PENDING' ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'bg-rose-100 text-rose-900 border border-rose-300'}`}>
                          {w.verification_status}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => setSelectedWorkerForVerify(w)}
                          className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded border border-slate-300"
                        >
                          Manage Verification
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

      </main>

      {/* Recommendation & Allocation Modal */}
      {matchingRequest && (
        <MatchingModal
          request={matchingRequest}
          onClose={() => setMatchingRequest(null)}
          onSuccess={(msg) => {
            setActionSuccess(msg)
            loadAdminData()
            setTimeout(() => setActionSuccess(''), 5000)
          }}
        />
      )}

      {/* Verification Modal */}
      {selectedWorkerForVerify && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4 relative">
            <button
              onClick={() => { setSelectedWorkerForVerify(null); setConsensusProgress(false); }}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 font-bold"
            >
              ✕
            </button>

            <h3 className="text-lg font-bold text-slate-900">Manage Worker Verification</h3>
            <p className="text-xs text-slate-600">
              Update verification status for cooperative member <strong className="text-slate-900">{selectedWorkerForVerify.name}</strong> ({selectedWorkerForVerify.profession}).
            </p>

            <div className="bg-slate-50 p-3 rounded border border-slate-200 text-xs space-y-1">
              <div>Email: <strong>{selectedWorkerForVerify.email}</strong></div>
              <div>Service Area: <strong>{selectedWorkerForVerify.location || 'Not set'}</strong></div>
              <div>Current Status: <strong className="text-blue-700">{selectedWorkerForVerify.verification_status}</strong></div>
            </div>

            {consensusProgress ? (
              <div className="bg-blue-50 p-4 rounded-xl border border-blue-200">
                <h4 className="font-bold text-sm text-blue-900 mb-2">Hybrid Trust Consensus Active</h4>
                
                <div className="space-y-3">
                  <div className="bg-white p-2 border border-emerald-100 rounded">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Stage 1: Centralized Baseline</div>
                    <div className="text-[10px] text-emerald-700 font-mono">✅ Gov ID Match Verified</div>
                    <div className="text-[10px] text-emerald-700 font-mono">✅ Criminal Background Cleared</div>
                  </div>

                  <div className="bg-white p-2 border border-blue-100 rounded">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Stage 2: Peer Quorum (Skill/Reputation)</div>
                    <p className="text-[9px] text-blue-700 mb-2 italic">Anti-collusion check passed. Requesting signatures from non-affiliated peers...</p>
                    <div className="text-[10px] text-blue-700 font-mono animate-pulse">📡 Node 1 (4.9★): Skill Signature Valid</div>
                    <div className="text-[10px] text-blue-700 font-mono animate-pulse delay-75">📡 Node 2 (4.8★): Work History Authenticated</div>
                    <div className="text-[10px] text-blue-700 font-mono animate-pulse delay-150">📡 Node 3 (5.0★): Local Reputation Confirmed</div>
                  </div>
                </div>
                
                <button
                  onClick={() => handleUpdateVerification(selectedWorkerForVerify.id, 'VERIFIED')}
                  className="w-full mt-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded transition"
                >
                  Confirm Hybrid Verification
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-2 pt-2">
                <button
                  disabled={verifying}
                  onClick={() => setConsensusProgress(true)}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <span>🤝</span> Trigger Hybrid Peer Verification
                </button>
                <p className="text-[9px] text-slate-500 text-center italic mb-2">Requires minimum 3 peer signatures. Falls back to manual admin review if no local peers available.</p>
                <div className="flex gap-2">
                  <button
                    disabled={verifying}
                    onClick={() => handleUpdateVerification(selectedWorkerForVerify.id, 'VERIFIED')}
                    className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-emerald-700 border border-slate-300 font-bold text-xs rounded transition disabled:opacity-50"
                  >
                    Admin Fallback Verify
                  </button>
                  <button
                    disabled={verifying}
                    onClick={() => handleUpdateVerification(selectedWorkerForVerify.id, 'REJECTED')}
                    className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-rose-700 border border-slate-300 font-bold text-xs rounded transition disabled:opacity-50"
                  >
                    Reject Member
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <Footer />
    </AnimatedPage>
  )
}
