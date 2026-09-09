import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

export default function FloatingWhatsAppWidget({ phoneNumber = '919999999999', companyName = 'Cooperative Support' }) {
  const [isOpen, setIsOpen] = useState(false)
  const [message, setMessage] = useState('')

  const handleSend = (e) => {
    e.preventDefault()
    if (!message.trim()) return
    const url = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(message)}`
    window.open(url, '_blank')
    setMessage('')
    setIsOpen(false)
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className="mb-4 w-72 bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-200"
          >
            {/* Header */}
            <div className="bg-[#075E54] p-4 flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center text-xl">
                🎧
              </div>
              <div>
                <h3 className="font-bold text-white text-sm leading-tight">{companyName}</h3>
                <p className="text-white/80 text-[10px]">Typically replies instantly</p>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="ml-auto text-white/80 hover:text-white"
              >
                ✕
              </button>
            </div>
            
            {/* Body */}
            <div className="bg-[#ECE5DD] p-4 h-32 overflow-y-auto">
              <div className="bg-white p-2 rounded-lg rounded-tl-none shadow-sm text-xs text-slate-800 max-w-[85%]">
                Hi there! 👋 How can we help you today?
              </div>
            </div>

            {/* Input */}
            <form onSubmit={handleSend} className="p-3 bg-white flex gap-2">
              <input 
                type="text" 
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type a message..."
                className="flex-1 bg-slate-100 rounded-full px-4 py-2 text-xs text-slate-900 outline-none focus:ring-2 focus:ring-[#25D366]"
                autoFocus
              />
              <button 
                type="submit"
                disabled={!message.trim()}
                className="w-8 h-8 rounded-full bg-[#128C7E] flex items-center justify-center text-white disabled:opacity-50 hover:bg-[#075E54] transition-colors"
              >
                ➤
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="w-14 h-14 bg-[#25D366] text-white rounded-full shadow-lg flex items-center justify-center text-3xl hover:bg-[#128C7E] transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
          <path d="M16.6 14c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1-.2.2-.6.8-.8 1-.1.2-.3.2-.5.1-.7-.3-1.4-.7-2-1.2-.5-.5-.8-1.1-1.1-1.7-.1-.2 0-.4.1-.5.1-.1.3-.3.4-.4.1-.1.2-.3.2-.4.1-.2 0-.4 0-.5C10 9 9.3 7.6 9 7c-.1-.4-.3-.4-.5-.4h-.4c-.2 0-.5.1-.7.3-.3.8.8-.8 2s.8 2.3 1 2.5c.2.2 1.7 2.6 4.1 3.6 2.4 1 2.4.7 2.8.6.4-.1 1.4-.6 1.6-1.1.2-.5.2-.9.1-1-.1-.1-.3-.2-.5-.3z"/>
          <path fillRule="evenodd" d="M12 2C6.48 2 2 6.48 2 12c0 1.7.4 3.4 1.2 4.9L2 22l5.3-1.1c1.5.8 3.1 1.2 4.8 1.2 5.5 0 10-4.5 10-10S17.5 2 12 2zm0 18c-1.5 0-3-.4-4.3-1.1l-.3-.2-3.2.7.7-3.1-.2-.3C4.2 14.8 3.7 13.4 3.7 12c0-4.6 3.7-8.3 8.3-8.3 4.6 0 8.3 3.7 8.3 8.3s-3.7 8.3-8.3 8.3z" clipRule="evenodd"/>
        </svg>
      </motion.button>
    </div>
  )
}
