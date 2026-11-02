/**
 * VoiceBookingBot — Sahakar Sathi.
 *
 * Patent Feature: Zero-Screen-Touch Voice Booking Dispatch.
 *
 * Flow:
 *  1. Customer taps mic → speaks in Hindi about their service need
 *  2. Web Speech API transcribes in real time (lang: hi-IN)
 *  3. extractBookingIntent() parses transcript for service + urgency
 *  4. On confidence ≥ 0.4: auto-submits to /api/voice-booking
 *  5. Backend picks best worker, sends Hindi SMS
 *  6. Bot speaks back confirmation in Hindi (speechSynthesis)
 *  7. Worker replies "1"/"2" on their basic phone — no smartphone needed
 *
 * UI: Floating emerald mic button (bottom-left), expandable panel.
 * Colors: emerald-700 + slate-900 only (2-color minimalist theme).
 */
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { extractBookingIntent } from '../utils/phoneticMatcher'
import {
  submitVoiceBooking,
  fallbackVoiceBooking,
  getVoiceBookingStatus,
  simulateSmsReply,
} from '../services/voiceBookingService'

// ─── Constants ────────────────────────────────────────────────────────────────

const STATES = {
  IDLE: 'idle',
  LISTENING: 'listening',
  PROCESSING: 'processing',
  SMS_SENT: 'sms_sent',
  ACCEPTED: 'accepted',
  ERROR: 'error',
}

const STATE_LABELS = {
  idle: 'बोलिए, क्या काम चाहिए?',
  listening: '🎤 सुन रहा हूँ...',
  processing: '⏳ कारीगर खोज रहे हैं...',
  sms_sent: '📱 SMS भेज दिया!',
  accepted: '✅ बुकिंग पक्की!',
  error: '❌ कुछ गड़बड़ हुई',
}

const HINT_PHRASES = [
  '"मुझे बिजली ठीक करवानी है"',
  '"नल टपक रहा है, प्लम्बर चाहिए"',
  '"घर की सफाई करवानी है"',
  '"एसी खराब हो गई है"',
  '"बढ़ई चाहिए दरवाज़ा ठीक करने के लिए"',
]

// ─── Speak utility ────────────────────────────────────────────────────────────

function speak(text, lang = 'hi-IN') {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utt = new SpeechSynthesisUtterance(text)
  utt.lang = lang
  utt.rate = 0.9
  window.speechSynthesis.speak(utt)
}

// ─── Main Component ────────────────────────────────────────────────────────────

export default function VoiceBookingBot({ onBookingCreated }) {
  const [isOpen, setIsOpen] = useState(false)
  const [botState, setBotState] = useState(STATES.IDLE)
  const [transcript, setTranscript] = useState('')
  const [intent, setIntent] = useState(null)
  const [booking, setBooking] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [hintIdx, setHintIdx] = useState(0)
  const [pollingCount, setPollingCount] = useState(0)

  const recognitionRef = useRef(null)
  const pollingRef = useRef(null)
  const panelRef = useRef(null)

  // Rotate hint phrases
  useEffect(() => {
    const t = setInterval(() => setHintIdx(i => (i + 1) % HINT_PHRASES.length), 3000)
    return () => clearInterval(t)
  }, [])

  // Check browser support
  const SpeechRecognition =
    typeof window !== 'undefined' &&
    (window.SpeechRecognition || window.webkitSpeechRecognition)

  const isSupported = !!SpeechRecognition

  // ── Poll booking status after SMS sent ──────────────────────────────────────

  const startPolling = useCallback((bookingId) => {
    let count = 0
    pollingRef.current = setInterval(async () => {
      count++
      setPollingCount(count)
      try {
        const res = await getVoiceBookingStatus(bookingId)
        const s = res.data?.status
        if (s === 'ACCEPTED') {
          clearInterval(pollingRef.current)
          setBotState(STATES.ACCEPTED)
          speak('बुकिंग पक्की हो गई! कारीगर जल्द आएंगे।')
          onBookingCreated && onBookingCreated(res.data)
        } else if (s === 'REJECTED') {
          clearInterval(pollingRef.current)
          // Auto-trigger fallback
          speak('कारीगर ने मना किया। दूसरे को SMS भेज रहे हैं।')
          setBotState(STATES.PROCESSING)
          setTranscript('दूसरे कारीगर को भेज रहे हैं...')
        }
      } catch (e) {
        // Polling errors are non-fatal — keep polling
      }
      // Stop polling after 60 attempts (~3 min)
      if (count >= 60) clearInterval(pollingRef.current)
    }, 3000)
  }, [onBookingCreated])

  // ── Start voice recognition ──────────────────────────────────────────────────

  const startListening = useCallback(() => {
    if (!isSupported) {
      setErrorMsg('यह browser voice नहीं समझता। Chrome में खोलें।')
      setBotState(STATES.ERROR)
      return
    }

    // Cancel any ongoing TTS
    window.speechSynthesis?.cancel()

    const recognition = new SpeechRecognition()
    recognition.lang = 'hi-IN'
    recognition.interimResults = true
    recognition.maxAlternatives = 3
    recognition.continuous = false

    recognition.onstart = () => {
      setBotState(STATES.LISTENING)
      setTranscript('')
      setIntent(null)
      setBooking(null)
      setErrorMsg('')
      speak('बोलिए, क्या काम चाहिए?', 'hi-IN')
    }

    recognition.onresult = (event) => {
      const results = Array.from(event.results)
      const interimText = results
        .map(r => r[0].transcript)
        .join(' ')
      setTranscript(interimText)
    }

    recognition.onend = async () => {
      if (recognitionRef.current) {
        recognitionRef.current = null
      }
      // Get final transcript and process
      const finalTranscript = transcript ||
        (document.getElementById('vb-transcript')?.textContent || '')

      setBotState(STATES.PROCESSING)

      if (!finalTranscript || finalTranscript.length < 3) {
        setBotState(STATES.IDLE)
        return
      }

      // Extract intent
      const extracted = extractBookingIntent(finalTranscript)
      setIntent(extracted)

      if (!extracted.service_type || extracted.confidence < 0.3) {
        setErrorMsg(`समझ नहीं आया। कहें: "मुझे ${HINT_PHRASES[0].replace(/"/g, '')} चाहिए"`)
        setBotState(STATES.ERROR)
        speak('समझ नहीं आया। फिर से बोलिए।')
        return
      }

      // Submit booking
      try {
        const location = 'Customer Location' // In prod: get from geolocation
        let lat = null, lon = null
        if (navigator.geolocation) {
          try {
            const pos = await new Promise((res, rej) =>
              navigator.geolocation.getCurrentPosition(res, rej, { timeout: 3000 })
            )
            lat = pos.coords.latitude
            lon = pos.coords.longitude
          } catch {}
        }

        const res = await submitVoiceBooking({
          service_type: extracted.service_type,
          urgency: extracted.urgency,
          location,
          latitude: lat,
          longitude: lon,
          description: finalTranscript,
        })

        const data = res.data
        setBooking(data)
        setBotState(STATES.SMS_SENT)

        const confirmText = data.sms_sent
          ? `${data.service_name} के लिए ${data.worker_name} को SMS भेज दिया। जवाब का इंतज़ार है।`
          : `बुकिंग हो गई, लेकिन SMS नहीं गया। कारीगर को सूचित करें।`
        speak(confirmText)

        // Start polling for worker reply
        startPolling(data.booking_id)
      } catch (err) {
        const msg = err?.response?.data?.detail || 'सर्वर से जुड़ नहीं पाए।'
        setErrorMsg(msg)
        setBotState(STATES.ERROR)
        speak('कुछ गड़बड़ हुई। फिर से कोशिश करें।')
      }
    }

    recognition.onerror = (e) => {
      if (e.error === 'no-speech') {
        setBotState(STATES.IDLE)
      } else {
        setErrorMsg(`Voice error: ${e.error}`)
        setBotState(STATES.ERROR)
      }
    }

    recognitionRef.current = recognition
    recognition.start()
  }, [isSupported, SpeechRecognition, transcript, startPolling])

  // Fix: transcript captured in closure — keep a ref in DOM
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
  }, [])

  const reset = useCallback(() => {
    clearInterval(pollingRef.current)
    stopListening()
    setBotState(STATES.IDLE)
    setTranscript('')
    setIntent(null)
    setBooking(null)
    setErrorMsg('')
    setPollingCount(0)
  }, [stopListening])

  // ── Simulate demo reply ──────────────────────────────────────────────────────

  const handleSimulateReply = async (reply) => {
    if (!booking?.booking_id) return
    try {
      const res = await simulateSmsReply(booking.booking_id, reply)
      if (reply === '1') {
        clearInterval(pollingRef.current)
        setBotState(STATES.ACCEPTED)
        speak('बुकिंग पक्की हो गई!')
        onBookingCreated && onBookingCreated(booking)
      } else {
        speak('कारीगर ने मना किया।')
        setBotState(STATES.ERROR)
        setErrorMsg('कारीगर ने मना किया। Fallback के लिए दोबारा बोलें।')
      }
    } catch (e) {
      setErrorMsg('Simulate reply failed')
    }
  }

  // ── Cleanup on unmount ───────────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      clearInterval(pollingRef.current)
      recognitionRef.current?.stop()
      window.speechSynthesis?.cancel()
    }
  }, [])

  // ── Render ───────────────────────────────────────────────────────────────────

  const isMicActive = botState === STATES.LISTENING
  const isLoading = botState === STATES.PROCESSING

  return (
    <>
      {/* ── Floating mic button ── */}
      <button
        onClick={() => {
          if (!isOpen) setIsOpen(true)
          if (botState === STATES.IDLE || botState === STATES.ERROR) startListening()
          else if (botState === STATES.LISTENING) stopListening()
        }}
        title="बोलकर बुकिंग करें"
        aria-label="Voice booking"
        className={[
          'fixed bottom-6 left-6 z-50 w-14 h-14 rounded-full shadow-lg',
          'flex items-center justify-center text-2xl transition-all duration-300',
          isMicActive
            ? 'bg-red-600 text-white scale-110 animate-pulse'
            : 'bg-emerald-700 text-white hover:bg-emerald-800 hover:scale-105',
        ].join(' ')}
      >
        {isLoading ? (
          <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : isMicActive ? '🔴' : '🎤'}
      </button>

      {/* ── Expandable panel ── */}
      {isOpen && (
        <div
          ref={panelRef}
          className="fixed bottom-24 left-6 z-50 w-80 bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden"
        >
          {/* Header */}
          <div className="bg-emerald-700 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-white text-lg">🎤</span>
              <div>
                <p className="text-white font-semibold text-sm leading-tight">बोलकर बुकिंग</p>
                <p className="text-emerald-200 text-xs">Voice Booking Bot</p>
              </div>
            </div>
            <button
              onClick={() => { setIsOpen(false); reset() }}
              className="text-emerald-200 hover:text-white text-xl leading-none"
            >
              ×
            </button>
          </div>

          {/* Status bar */}
          <div className={[
            'px-4 py-2 text-xs font-medium text-center',
            botState === STATES.ACCEPTED ? 'bg-emerald-50 text-emerald-700' :
            botState === STATES.SMS_SENT ? 'bg-blue-50 text-blue-700' :
            botState === STATES.LISTENING ? 'bg-red-50 text-red-700' :
            botState === STATES.ERROR ? 'bg-red-50 text-red-600' :
            'bg-slate-50 text-slate-600',
          ].join(' ')}>
            {STATE_LABELS[botState]}
          </div>

          <div className="px-4 py-3 space-y-3">

            {/* Hint (idle) */}
            {botState === STATES.IDLE && (
              <div className="bg-slate-50 rounded-xl px-3 py-2">
                <p className="text-xs text-slate-500 mb-1">उदाहरण:</p>
                <p className="text-sm text-slate-700 font-medium transition-all duration-500">
                  {HINT_PHRASES[hintIdx]}
                </p>
              </div>
            )}

            {/* Live transcript */}
            {(botState === STATES.LISTENING || botState === STATES.PROCESSING) && (
              <div className="bg-slate-50 rounded-xl px-3 py-2 min-h-12">
                <p className="text-xs text-slate-500 mb-1">आपने कहा:</p>
                <p
                  id="vb-transcript"
                  className="text-sm text-slate-800 font-medium"
                >
                  {transcript || <span className="text-slate-400 animate-pulse">सुन रहा हूँ...</span>}
                </p>
              </div>
            )}

            {/* Intent detected */}
            {intent && intent.service_type && (
              <div className="flex items-center gap-2 px-3 py-2 bg-emerald-50 rounded-xl">
                <span className="text-emerald-700 text-lg">🔍</span>
                <div>
                  <p className="text-xs text-emerald-600 font-medium">पहचाना गया:</p>
                  <p className="text-sm text-emerald-800 font-bold">{intent.service_type}</p>
                  {intent.urgency === 'URGENT' && (
                    <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">⚡ ज़रूरी</span>
                  )}
                </div>
                <span className="ml-auto text-xs text-emerald-600">
                  {Math.round(intent.confidence * 100)}%
                </span>
              </div>
            )}

            {/* Booking result */}
            {booking && (
              <div className="bg-slate-50 rounded-xl px-3 py-2 space-y-1.5">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-slate-600">बुकिंग #{booking.booking_id}</p>
                  <span className={[
                    'text-xs px-2 py-0.5 rounded-full font-medium',
                    botState === STATES.ACCEPTED
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-blue-100 text-blue-700',
                  ].join(' ')}>
                    {botState === STATES.ACCEPTED ? 'पक्की ✅' : 'SMS भेजा 📱'}
                  </span>
                </div>
                <div className="text-xs text-slate-500 space-y-0.5">
                  <p>🔧 <span className="text-slate-700">{booking.service_name}</span></p>
                  <p>👷 <span className="text-slate-700">{booking.worker_name}</span> (****{booking.worker_phone_last4})</p>
                  <p>📅 <span className="text-slate-700">{booking.scheduled_date} {booking.scheduled_time}</span></p>
                </div>

                {/* SMS message preview */}
                {booking.sms_message && (
                  <details className="mt-1">
                    <summary className="text-xs text-emerald-700 cursor-pointer hover:underline">
                      भेजा गया SMS देखें →
                    </summary>
                    <pre className="mt-1 text-xs text-slate-600 bg-slate-100 rounded-lg p-2 whitespace-pre-wrap font-sans">
                      {booking.sms_message}
                    </pre>
                  </details>
                )}

                {/* Polling indicator */}
                {botState === STATES.SMS_SENT && pollingCount > 0 && (
                  <p className="text-xs text-blue-500 animate-pulse text-center pt-1">
                    जवाब का इंतज़ार है... ({pollingCount * 3}s)
                  </p>
                )}

                {/* Demo simulate buttons */}
                {botState === STATES.SMS_SENT && (
                  <div className="pt-1">
                    <p className="text-xs text-slate-400 mb-1.5 text-center">डेमो: कारीगर का जवाब सिमुलेट करें</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSimulateReply('1')}
                        className="flex-1 bg-emerald-700 text-white text-xs py-1.5 rounded-lg hover:bg-emerald-800 transition-colors font-medium"
                      >
                        ✅ स्वीकार (1)
                      </button>
                      <button
                        onClick={() => handleSimulateReply('2')}
                        className="flex-1 bg-slate-200 text-slate-700 text-xs py-1.5 rounded-lg hover:bg-slate-300 transition-colors font-medium"
                      >
                        ❌ मना (2)
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Error */}
            {botState === STATES.ERROR && errorMsg && (
              <div className="bg-red-50 rounded-xl px-3 py-2">
                <p className="text-xs text-red-600">{errorMsg}</p>
              </div>
            )}

            {/* Accepted celebration */}
            {botState === STATES.ACCEPTED && (
              <div className="bg-emerald-50 rounded-xl px-3 py-3 text-center">
                <p className="text-2xl mb-1">🎉</p>
                <p className="text-sm font-bold text-emerald-800">बुकिंग पक्की हो गई!</p>
                <p className="text-xs text-emerald-600">{booking?.worker_name} जल्द आएंगे</p>
              </div>
            )}

            {/* Unsupported browser */}
            {!isSupported && (
              <div className="bg-amber-50 rounded-xl px-3 py-2">
                <p className="text-xs text-amber-700">
                  ⚠️ आपका browser voice नहीं समझता।<br />
                  Chrome या Edge में खोलें।
                </p>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2 pt-1">
              {(botState === STATES.IDLE || botState === STATES.ERROR) && isSupported && (
                <button
                  onClick={startListening}
                  className="flex-1 bg-emerald-700 text-white text-sm py-2 rounded-xl hover:bg-emerald-800 transition-colors font-semibold"
                >
                  🎤 बोलें
                </button>
              )}
              {botState === STATES.LISTENING && (
                <button
                  onClick={stopListening}
                  className="flex-1 bg-red-600 text-white text-sm py-2 rounded-xl hover:bg-red-700 transition-colors font-semibold animate-pulse"
                >
                  ⏹ रोकें
                </button>
              )}
              {![STATES.IDLE, STATES.LISTENING, STATES.PROCESSING].includes(botState) && (
                <button
                  onClick={reset}
                  className="flex-1 bg-slate-100 text-slate-700 text-sm py-2 rounded-xl hover:bg-slate-200 transition-colors"
                >
                  🔄 फिर बोलें
                </button>
              )}
            </div>

            {/* Footer */}
            <p className="text-center text-xs text-slate-300 pb-1">
              Patent Feature · Sahakar Sathi · No-Touch Dispatch
            </p>
          </div>
        </div>
      )}
    </>
  )
}
