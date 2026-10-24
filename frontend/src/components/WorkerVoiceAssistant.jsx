import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { parseConfirmation } from '../utils/parseConfirmation'
import { fuzzyMatchIntent } from '../utils/phoneticMatcher'

export default function WorkerVoiceAssistant({ 
  workerName = 'Worker', 
  jobs = [], 
  onAcceptJob, 
  onStartJob 
}) {
  const [lang, setLang] = useState('hi')
  const isHindi = lang === 'hi'
  
  const [isOpen, setIsOpen] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)
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

  // Calculate earnings & jobs
  const completedJobs = jobs.filter(j => j.status === 'COMPLETED')
  const totalEarnings = completedJobs.reduce((sum, j) => sum + (j.amount || 0), 0)
  const assignedJobs = jobs.filter(j => j.status === 'ASSIGNED')
  const acceptedJobs = jobs.filter(j => j.status === 'ACCEPTED')

  // Open assistant and greet in Hindi
  const handleOpen = () => {
    setIsOpen(true)
    const greeting = isHindi 
      ? `नमस्ते ${workerName} जी! मैं आपका वॉयस असिस्टेंट हूँ। बताइये, मैं आपकी कैसे मदद करूँ?`
      : `Hello ${workerName}! I am your voice assistant. How can I help you today?`
    setAssistantMessage(greeting)
    speak(greeting)
  }

  const handleCommand = (cmdText) => {
    const text = cmdText.toLowerCase().trim()
    
    // Handle pending confirmations
    if (pendingAction) {
      const parsed = parseConfirmation(text)
      
      if (parsed === 'yes') {
        if (pendingAction.type === 'ACCEPT') {
          onAcceptJob && onAcceptJob(pendingAction.jobId)
          const msg = isHindi ? 'काम स्वीकार कर लिया गया है।' : 'Job accepted.'
          speak(msg)
          setAssistantMessage(msg)
        } else if (pendingAction.type === 'START') {
          onStartJob && onStartJob(pendingAction.jobId)
          const msg = isHindi ? 'काम शुरू हो गया है।' : 'Job started.'
          speak(msg)
          setAssistantMessage(msg)
        }
        setPendingAction(null)
      } else if (parsed === 'no') {
        const msg = isHindi ? 'कार्रवाई रद्द कर दी गई।' : 'Action cancelled.'
        speak(msg)
        setAssistantMessage(msg)
        setPendingAction(null)
      } else {
        if (!pendingAction.retry) {
          const msg = isHindi ? 'क्षमा करें, मुझे समझ नहीं आया। कृपया हां या ना कहें।' : 'Sorry, I didn\'t catch that. Please say yes or no.'
          speak(msg)
          setAssistantMessage(msg)
          setPendingAction({ ...pendingAction, retry: true })
        } else {
          const msg = isHindi ? 'क्षमा करें, कार्रवाई रद्द कर दी गई।' : 'Sorry, action cancelled.'
          speak(msg)
          setAssistantMessage(msg)
          setPendingAction(null)
        }
      }
      setTranscript('')
      return
    }

    setTranscript(text)

    // Define fuzzy intent targets for different actions
    const earningsIntents = ['कमाई', 'पैसे', 'earning', 'balance', 'wallet', 'kamaai', 'kamayee', 'paisa', 'check earnings']
    const jobsIntents = ['काम', 'job', 'order', 'kaam', 'naya', 'new jobs']
    const acceptIntents = ['स्वीकार', 'accept', 'ha', 'yes', 'haan', 'theek', 'karo', 'काम स्वीकार']
    const startIntents = ['शुरू', 'start', 'chalu', 'shuru']

    // 1. Check Earnings
    if (fuzzyMatchIntent(text, earningsIntents)) {
      const reply = isHindi 
        ? `${workerName} जी, आपकी कुल कमाई ₹${totalEarnings} है, और आपने ${completedJobs.length} काम सफलतापूर्वक पूरे किए हैं।`
        : `${workerName}, your wallet balance is ₹${totalEarnings}, with ${completedJobs.length} completed jobs.`
      setAssistantMessage(reply)
      speak(reply)
      return
    }

    // 2. Check New Jobs
    if (fuzzyMatchIntent(text, jobsIntents)) {
      if (assignedJobs.length > 0) {
        const first = assignedJobs[0]
        const reply = isHindi 
          ? `आपके पास ${assignedJobs.length} नया काम है: ${first.service_name}। स्थान है ${first.location}। ग्राहक आपको ₹${first.amount || 499} भुगतान करेंगे। क्या आप इसे स्वीकार करना चाहेंगे?`
          : `You have ${assignedJobs.length} new job: ${first.service_name} at ${first.location}. Payout is ₹${first.amount || 499}. Would you like to accept it?`
        setAssistantMessage(reply)
        speak(reply)
        setPendingAction({ type: 'ACCEPT', jobId: first.id, retry: false })
      } else if (acceptedJobs.length > 0) {
        const first = acceptedJobs[0]
        const reply = isHindi 
          ? `आपने ${first.service_name} को स्वीकार कर लिया है। क्या आप इसे शुरू करना चाहेंगे?`
          : `You have accepted ${first.service_name}. Would you like to start it?`
        setAssistantMessage(reply)
        speak(reply)
        setPendingAction({ type: 'START', jobId: first.id, retry: false })
      } else {
        const reply = isHindi 
          ? `अभी कोई नया काम नहीं है। जब कोई काम आएगा तो मैं आपको बता दूंगा।`
          : `You currently have no pending jobs. I will notify you when a new job arrives.`
        setAssistantMessage(reply)
        speak(reply)
      }
      return
    }

    // 3. Accept Job
    if (fuzzyMatchIntent(text, acceptIntents)) {
      if (assignedJobs.length > 0) {
        const first = assignedJobs[0]
        onAcceptJob && onAcceptJob(first.id)
        const reply = isHindi 
          ? `काम स्वीकार कर लिया गया है! ग्राहक ${first.customer_name} को सूचित कर दिया गया है।`
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
    if (fuzzyMatchIntent(text, startIntents)) {
      if (acceptedJobs.length > 0) {
        const first = acceptedJobs[0]
        onStartJob && onStartJob(first.id)
        const reply = isHindi 
          ? `काम शुरू हो गया है! कृपया सुरक्षित रूप से अपना काम पूरा करें।`
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

    // Fallback Unrecognized
    const reply = isHindi 
      ? `मुझे समझ नहीं आया। क्या आप कह सकते हैं: 'मेरी कमाई बताओ', 'नया काम बताओ', या 'काम स्वीकार करो'?`
      : `Sorry, I did not catch that. You can say: 'check earnings', 'show new jobs', or 'accept job'.`
    setAssistantMessage(reply)
    speak(reply)
  }

  const toggleListen = () => {
    if (isListening) {
      recognitionRef.current?.stop()
      return
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert("Browser does not support speech recognition. Use Chrome.")
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = isHindi ? 'hi-IN' : 'en-US'
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onstart = () => {
      setIsListening(true)
      setTranscript(isHindi ? 'सुन रहा हूँ... बोलिये' : 'Listening...')
    }

    recognition.onresult = (e) => {
      const text = e.results[0][0].transcript
      handleCommand(text)
    }

    recognition.onerror = () => {
      setIsListening(false)
      setTranscript('')
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition
    recognition.start()
  }

  return (
    <>
      <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-3">
        <AnimatePresence>
          {isOpen && (
            <motion.div
              className="bg-white rounded-2xl shadow-2xl border border-emerald-100 w-80 overflow-hidden"
              initial={{ opacity: 0, y: 50, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 50, scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            >
              <div className="bg-emerald-50 p-4 border-b border-emerald-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <motion.div 
                    className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 text-xl"
                    animate={isListening ? { scale: [1, 1.2, 1] } : {}}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                  >
                    🎙️
                  </motion.div>
                  <div>
                    <h3 className="font-bold text-slate-800 text-sm">
                      {isHindi ? 'सहकार वॉयस असिस्टेंट' : 'Sahakar Voice Assistant'}
                    </h3>
                    <p className="text-[11px] font-medium text-emerald-600">
                      {isHindi ? '🎙 आवाज़ से चलने वाला असिस्टेंट' : '🎙 Voice-controlled gig assistant'}
                    </p>
                  </div>
                </div>
                <div className="flex gap-1">
                  <button 
                    onClick={() => setLang(isHindi ? 'en' : 'hi')}
                    className="px-2 py-1 bg-white border border-slate-200 text-slate-600 text-[10px] font-bold rounded-lg shadow-sm hover:bg-slate-50 transition"
                  >
                    {isHindi ? 'ENG' : 'हिंदी'}
                  </button>
                  <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-slate-700">✖</button>
                </div>
              </div>

              <div className="p-5 space-y-4">
                <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 text-xs text-slate-700 space-y-2">
                  <div className="font-bold text-slate-500">
                  <span>🤖</span> {isHindi ? 'असिस्टेंट मैसेज (आपसे बात कर रहा है):' : 'Assistant Message:'}
                  </div>
                  <p className="font-medium text-slate-900 leading-relaxed">{assistantMessage || '...'}</p>
                </div>

                {transcript && (
                  <div className="text-right">
                    <span className="text-xs text-slate-500 block mb-1">
                      <span>🗣️</span> <strong>{isHindi ? 'आपने कहा:' : 'You said:'}</strong> "{transcript}"
                    </span>
                  </div>
                )}
                
                <div className="flex justify-center pt-2">
                  <button 
                    onClick={toggleListen}
                    className={`flex items-center justify-center gap-2 px-6 py-3 rounded-full font-bold shadow-lg transition-all ${
                      isListening 
                        ? 'bg-rose-500 text-white scale-110 shadow-rose-500/50' 
                        : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/30'
                    }`}
                  >
                    <span className="text-2xl">{isListening ? '🛑' : '🎤'}</span>
                    <span>
                      {isListening ? (isHindi ? 'रुकें' : 'Stop') : (isHindi ? 'बोलें' : 'Speak')}
                    </span>
                  </button>
                </div>

                <div className="text-center text-[10px] text-slate-500 mt-2 font-medium">
                  {isListening 
                    ? (isHindi ? 'मैं सुन रहा हूँ... साफ़ बोलें!' : '🟢 Listening now... speak clearly!') 
                    : (isHindi ? 'बोलने के लिए माइक दबाएं' : 'Tap mic to speak command')}
                </div>

                <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-2 justify-center">
                  <span className="text-[10px] text-slate-400 w-full text-center mb-1">
                    {isHindi ? 'या तुरंत कमांड दबाएं:' : 'Or tap a quick command:'}
                  </span>
                  {[
                    { en: 'check earnings', hi: 'कमाई बताओ' },
                    { en: 'new jobs', hi: 'नया काम बताओ' },
                    { en: 'accept', hi: 'काम स्वीकार करो' },
                    { en: 'start', hi: 'काम शुरू करो' }
                  ].map(cmd => (
                    <button 
                      key={cmd.en}
                      onClick={() => handleCommand(cmd.hi)}
                      className="px-2 py-1 bg-white border border-slate-200 text-slate-600 rounded-md text-[10px] hover:bg-slate-50 hover:border-slate-300 transition"
                    >
                      {isHindi ? cmd.hi : cmd.en}
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!isOpen && (
          <motion.button
            onClick={handleOpen}
            className="w-14 h-14 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full flex items-center justify-center text-white shadow-xl shadow-emerald-500/30 hover:shadow-2xl transition"
            whileHover={{ scale: 1.1, rotate: 5 }}
            whileTap={{ scale: 0.95 }}
          >
            <span className="text-2xl">🎤</span>
          </motion.button>
        )}
      </div>
    </>
  )
}
