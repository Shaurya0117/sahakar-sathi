import React, { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useLanguage } from '../context/LanguageContext'

export default function WorkerVoiceAssistant({ 
  workerName = 'विशाल',
  jobs = [], 
  onAcceptJob, 
  onStartJob 
}) {
  const { language } = useLanguage()
  const isHindi = language === 'hi'
  const [isOpen, setIsOpen] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [assistantMessage, setAssistantMessage] = useState('')
  const recognitionRef = useRef(null)

  // Voice synthesis helper
  const speak = (text) => {
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = isHindi ? 'hi-IN' : 'en-US'
    utterance.rate = 0.95
    window.speechSynthesis.speak(utterance)
  }

  // Calculate earnings
  const completedJobs = jobs.filter(j => j.status === 'COMPLETED')
  const totalEarnings = completedJobs.reduce((sum, j) => sum + (j.amount || 0), 0)
  const assignedJobs = jobs.filter(j => j.status === 'ASSIGNED')
  const acceptedJobs = jobs.filter(j => j.status === 'ACCEPTED')

  // Open assistant and greet
  const handleOpen = () => {
    setIsOpen(true)
    const greeting = isHindi 
      ? `नमस्ते ${workerName} जी! मैं आपका आवाज़ सहायक हूँ। बोलिए, मैं क्या सहायता करूँ?`
      : `Hello ${workerName}! I am your voice assistant. How can I help you today?`
    setAssistantMessage(greeting)
    speak(greeting)
  }

  const handleClose = () => {
    setIsOpen(false)
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch (e) {}
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
  }

  // Handle Voice Commands
  const processCommand = (cmdText) => {
    const text = cmdText.toLowerCase().trim()
    setTranscript(text)

    // 1. Check Earnings
    if (text.includes('कमाई') || text.includes('पैसे') || text.includes('earning') || text.includes('balance') || text.includes('wallet')) {
      const reply = isHindi 
        ? `${workerName} जी, आपके वॉलेट में कुल ₹${totalEarnings} हैं, और आपने ${completedJobs.length} काम पूरे किए हैं।`
        : `${workerName}, your wallet has ₹${totalEarnings}, with ${completedJobs.length} completed jobs.`
      setAssistantMessage(reply)
      speak(reply)
      return
    }

    // 2. Check Jobs
    if (text.includes('काम') || text.includes('job') || text.includes('नया') || text.includes('order')) {
      if (assignedJobs.length > 0) {
        const first = assignedJobs[0]
        const reply = isHindi 
          ? `आपके पास ${assignedJobs.length} नया काम है। ${first.service_name}, स्थान है ${first.location}। क्या इसे स्वीकार करना है?`
          : `You have ${assignedJobs.length} new job. ${first.service_name} at ${first.location}. Would you like to accept it?`
        setAssistantMessage(reply)
        speak(reply)
      } else if (acceptedJobs.length > 0) {
        const first = acceptedJobs[0]
        const reply = isHindi 
          ? `आपने ${first.service_name} का काम स्वीकार किया हुआ है। क्या आप काम शुरू करना चाहते हैं?`
          : `You have accepted ${first.service_name}. Would you like to start it?`
        setAssistantMessage(reply)
        speak(reply)
      } else {
        const reply = isHindi 
          ? `फिलहाल आपके पास कोई नया काम लंबित नहीं है। जैसे ही काम आएगा, मैं आपको बताऊँगा।`
          : `You currently have no pending jobs. I will notify you when a new job arrives.`
        setAssistantMessage(reply)
        speak(reply)
      }
      return
    }

    // 3. Accept Job
    if (text.includes('स्वीकार') || text.includes('accept') || text.includes('ha') || text.includes('yes')) {
      if (assignedJobs.length > 0) {
        const first = assignedJobs[0]
        onAcceptJob && onAcceptJob(first.id)
        const reply = isHindi 
          ? `काम स्वीकार कर लिया गया है! ग्राहक ${first.customer_name} को सूचना भेज दी गई है।`
          : `Job accepted successfully! Notification sent to customer ${first.customer_name}.`
        setAssistantMessage(reply)
        speak(reply)
      } else {
        const reply = isHindi ? `स्वीकार करने के लिए कोई नया काम नहीं है।` : `No pending jobs to accept.`
        setAssistantMessage(reply)
        speak(reply)
      }
      return
    }

    // 4. Start Job
    if (text.includes('शुरू') || text.includes('start') || text.includes('chalu')) {
      if (acceptedJobs.length > 0) {
        const first = acceptedJobs[0]
        onStartJob && onStartJob(first.id)
        const reply = isHindi 
          ? `काम शुरू कर दिया गया है। अपना काम ध्यान से करें और पूरा होने पर सेंसर सत्यापन दबाएं!`
          : `Job marked in progress. Complete your service safely!`
        setAssistantMessage(reply)
        speak(reply)
      } else {
        const reply = isHindi ? `शुरू करने के लिए कोई स्वीकृत काम नहीं है।` : `No accepted job ready to start.`
        setAssistantMessage(reply)
        speak(reply)
      }
      return
    }

    // Fallback help
    const reply = isHindi 
      ? `माफ़ कीजिये, मैं समझ नहीं पाया। आप बोल सकते हैं: 'मेरी कमाई बताओ', 'नया काम बताओ', या 'काम स्वीकार करो'।`
      : `Sorry, I did not catch that. You can say: 'check earnings', 'show new jobs', or 'accept job'.`
    setAssistantMessage(reply)
    speak(reply)
  }

  // Toggle listening
  const toggleListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please use Google Chrome or Edge.')
      return
    }

    if (isListening) {
      try { recognitionRef.current.stop() } catch (e) {}
      setIsListening(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = isHindi ? 'hi-IN' : 'en-US'
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onstart = () => {
      setIsListening(true)
      setTranscript(isHindi ? 'सुन रहा हूँ... बोलिए' : 'Listening...')
    }

    recognition.onresult = (event) => {
      const speech = event.results[0][0].transcript
      processCommand(speech)
    }

    recognition.onerror = () => {
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
    } catch (e) {
      setIsListening(false)
    }
  }

  return (
    <>
      {/* ── Floating Voice Button (Worker Snabbit Style) ──────────────── */}
      <motion.div
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.5, type: 'spring' }}
      >
        <button
          onClick={handleOpen}
          className="flex items-center gap-2.5 px-4 py-3 bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 text-white font-extrabold text-xs rounded-full shadow-2xl hover:shadow-blue-500/50 hover:scale-105 transition-all border-2 border-white/20 group cursor-pointer"
          title="Voice Assistant for Workers"
        >
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <span className="text-lg">🎙️</span>
          <span>{isHindi ? 'आवाज़ सहायक' : 'Voice Assistant'}</span>
        </button>
      </motion.div>

      {/* ── Interactive Voice Assistant Modal ─────────────────────────── */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, y: 50, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 50, scale: 0.95 }}
              className="bg-white rounded-3xl p-6 max-w-md w-full shadow-2xl border border-slate-200 relative overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-9 h-9 rounded-2xl bg-blue-100 text-blue-700 flex items-center justify-center text-lg font-bold">
                    🎙️
                  </div>
                  <div>
                    <h3 className="font-extrabold text-slate-900 text-sm">
                      {isHindi ? 'सहकार साथी आवाज़ सहायक' : 'Sahakar Voice Assistant'}
                    </h3>
                    <p className="text-[10px] text-slate-500">
                      {isHindi ? 'आवाज़ से काम स्वीकारें और कमाई जानें' : 'Voice-controlled gig workflow'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleClose}
                  className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 flex items-center justify-center font-bold text-xs cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {/* Assistant Message Speech Bubble */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50/60 border border-blue-100 rounded-2xl p-4 text-xs text-slate-800 space-y-2 mb-4">
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-blue-700 uppercase tracking-wider">
                  <span>🤖</span> {isHindi ? 'सहायक संदेश' : 'Assistant'}
                </div>
                <p className="font-semibold text-slate-900 leading-relaxed text-sm">
                  "{assistantMessage}"
                </p>
                {transcript && (
                  <p className="text-[11px] text-slate-500 italic pt-1 border-t border-blue-100">
                    🗣️ {isHindi ? 'आपने कहा:' : 'You said:'} "{transcript}"
                  </p>
                )}
              </div>

              {/* Big Mic Push-to-Talk Button with Waves */}
              <div className="text-center py-3">
                <div className="relative inline-block">
                  {isListening && (
                    <div className="absolute inset-0 rounded-full bg-blue-400 animate-ping opacity-40"></div>
                  )}
                  <button
                    onClick={toggleListening}
                    className={`w-20 h-20 rounded-full flex flex-col items-center justify-center shadow-xl transition-all cursor-pointer ${
                      isListening
                        ? 'bg-rose-500 text-white scale-110 shadow-rose-500/50'
                        : 'bg-gradient-to-tr from-blue-600 to-indigo-600 text-white hover:scale-105 shadow-blue-500/40'
                    }`}
                  >
                    <span className="text-2xl">{isListening ? '⏹️' : '🎙️'}</span>
                    <span className="text-[9px] font-extrabold uppercase mt-1">
                      {isListening ? (isHindi ? 'रूकें' : 'Stop') : (isHindi ? 'बोलें' : 'Speak')}
                    </span>
                  </button>
                </div>
                <p className="text-xs text-slate-500 font-medium mt-3">
                  {isListening
                    ? (isHindi ? '🔴 मैं सुन रहा हूँ... बोलिए!' : '🔴 Listening now... speak clearly!')
                    : (isHindi ? 'माइक दबाएं और बोलें' : 'Tap mic to speak command')}
                </p>
              </div>

              {/* Quick Action Chips (For Low-Literacy Easy Tap) */}
              <div className="pt-4 border-t border-slate-100 mt-3">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  {isHindi ? 'या नीचे दिए विकल्पों पर दबाएं:' : 'Or tap a quick command:'}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => processCommand('मेरी कमाई बताओ')}
                    className="p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl text-left border border-slate-200 text-xs font-bold text-slate-700 flex items-center gap-2 transition cursor-pointer"
                  >
                    <span>💰</span>
                    <span>{isHindi ? 'मेरी कमाई बताओ' : 'Check Earnings'}</span>
                  </button>
                  <button
                    onClick={() => processCommand('नया काम बताओ')}
                    className="p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl text-left border border-slate-200 text-xs font-bold text-slate-700 flex items-center gap-2 transition cursor-pointer"
                  >
                    <span>📋</span>
                    <span>{isHindi ? 'नया काम बताओ' : 'Check New Jobs'}</span>
                  </button>
                  <button
                    onClick={() => processCommand('काम स्वीकार करो')}
                    className="p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl text-left border border-slate-200 text-xs font-bold text-slate-700 flex items-center gap-2 transition cursor-pointer"
                  >
                    <span>✅</span>
                    <span>{isHindi ? 'काम स्वीकार करो' : 'Accept Job'}</span>
                  </button>
                  <button
                    onClick={() => processCommand('काम शुरू करो')}
                    className="p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl text-left border border-slate-200 text-xs font-bold text-slate-700 flex items-center gap-2 transition cursor-pointer"
                  >
                    <span>🚀</span>
                    <span>{isHindi ? 'काम शुरू करो' : 'Start Job'}</span>
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
