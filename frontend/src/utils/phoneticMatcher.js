/**
 * Patent Feature: Accessibility-First Voice-Driven Gig Management.
 * 
 * Implements Levenshtein distance and Phonetic similarity for fuzzy intent matching.
 * Crucial for low-literacy workers speaking in regional dialects (e.g. Hindi, Marathi)
 * where speech-to-text might misspell or use phonetic variations.
 */

/**
 * Calculates the Levenshtein distance between two strings.
 */
function levenshteinDistance(a, b) {
  const matrix = []
  
  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i]
  }
  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j
  }
  
  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1]
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // substitution
          Math.min(matrix[i][j - 1] + 1, // insertion
          matrix[i - 1][j] + 1) // deletion
        )
      }
    }
  }
  return matrix[b.length][a.length]
}

/**
 * Transliterates Devanagari to Latin characters roughly so phonetic rules apply.
 */
function transliterateDevanagari(str) {
  if (!str) return '';
  const devanagariMap = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n'
  };
  
  let result = '';
  for (let i = 0; i < str.length; i++) {
    const char = str[i];
    result += devanagariMap[char] || char;
  }
  return result;
}

/**
 * Very basic Soundex-style phonetic normalization for Hindi/English variations.
 * Strips vowels and groups similar sounding consonants.
 */
function phoneticNormalize(str) {
  if (!str) return ''
  let s = transliterateDevanagari(str.toLowerCase());
  s = s.replace(/[^a-z0-9\s]/g, '')
  
  // Hindi/English phonetic normalization rules
  s = s.replace(/sh/g, 's')
  s = s.replace(/ee/g, 'i')
  s = s.replace(/oo/g, 'u')
  s = s.replace(/v/g, 'w')
  s = s.replace(/ph/g, 'f')
  s = s.replace(/z/g, 'j')
  
  // Remove vowels (except first letter) to catch spelling variations
  if (s.length > 1) {
    s = s.charAt(0) + s.substring(1).replace(/[aeiouy]/g, '')
  }
  return s
}

/**
 * Checks if transcript matches any of the target phrases using fuzzy logic.
 * Returns true if exact match, substring match, or fuzzy phonetic match within threshold.
 */
export function fuzzyMatchIntent(transcript, targetPhrases, threshold = 2, requiresStrict = false) {
  if (!transcript || !targetPhrases || targetPhrases.length === 0) return false
  
  const lowerTranscript = transcript.toLowerCase().trim()
  const words = lowerTranscript.split(' ')
  
  for (const phrase of targetPhrases) {
    const lowerPhrase = phrase.toLowerCase().trim()
    
    // 1. Exact or substring match (most common)
    if (lowerTranscript.includes(lowerPhrase) || lowerPhrase.includes(lowerTranscript)) {
      return true
    }
    
    // 2. Word-by-word fuzzy match (Levenshtein + Phonetic)
    const phraseWords = lowerPhrase.split(' ')
    let matchedWords = 0
    
    for (const pw of phraseWords) {
      let wordMatched = false
      for (const tw of words) {
        // Direct Levenshtein on word
        if (levenshteinDistance(pw, tw) <= threshold) {
            wordMatched = true
            break
        }
        
        // Handle Devanagari direct match
        if (levenshteinDistance(transliterateDevanagari(pw), transliterateDevanagari(tw)) <= threshold) {
            wordMatched = true
            break
        }

        // Phonetic Levenshtein (e.g. "kamaai" vs "kamayee")
        if (levenshteinDistance(phoneticNormalize(pw), phoneticNormalize(tw)) <= 1) {
          wordMatched = true
          break
        }
      }
      if (wordMatched) matchedWords++
    }
    
    // If strict match required (e.g. for "accept"), we need 100% of the phrase words to match, 
    // otherwise 70% is enough.
    const matchRatio = requiresStrict ? 1.0 : 0.7;
    if (phraseWords.length > 0 && matchedWords / phraseWords.length >= matchRatio) {
      return true
    }
  }
  
  return false
}


// ============================================================================
// Patent Feature: Voice Booking Intent Extraction
// Zero-Screen-Touch — customer speaks, bot extracts and dispatches.
// ============================================================================

/**
 * Service keyword map.
 * Keys must match backend service names / categories (case-insensitive).
 */
const SERVICE_MAP = {
  electrician: [
    'bijli', 'bijlee', 'बिजली', 'electric', 'electricity', 'wiring', 'wire',
    'fan', 'switch', 'light', 'bulb', 'socket', 'mcb', 'fuse', 'current',
    'bijali', 'light band', 'switch thik', 'wireman',
  ],
  plumber: [
    'nal', 'nala', 'नल', 'pipe', 'paani', 'pani', 'पानी', 'leak', 'leakage',
    'plumber', 'plumbing', 'tapkana', 'tap', 'sink', 'toilet', 'commode',
    'bathroom pipe', 'geysir', 'geyser', 'pani nahi aa raha', 'naali',
  ],
  cleaner: [
    'safai', 'सफाई', 'clean', 'cleaning', 'jhadoo', 'बर्तन', 'bartan',
    'mop', 'sweep', 'ghar saaf', 'deep clean', 'bathroom clean', 'toilet clean',
    'saaf karna', 'house clean', 'home clean',
  ],
  carpenter: [
    'badhai', 'badhyee', 'बढ़ई', 'carpenter', 'carpentry', 'wood', 'lakdi',
    'furniture', 'door', 'darwaza', 'almirah', 'table', 'chair', 'repair wood',
    'darwaza thik', 'khidki', 'window',
  ],
  'ac repair': [
    'ac', 'एसी', 'cooler', 'aircondition', 'air condition', 'aircon',
    'ac thik', 'ac kharab', 'ac service', 'ac safai', 'ac gas', 'refrigerator',
    'fridge', 'freeze', 'thanda nahi', 'cooling nahi',
  ],
  painter: [
    'rang', 'रंग', 'paint', 'painting', 'colour', 'color', 'rangai', 'रंगाई',
    'wall paint', 'ghar paint', 'painter', 'distemper', 'whitewash', 'colour karna',
    'putal', 'lime',
  ],
  'pest control': [
    'kide', 'कीड़े', 'pest', 'termite', 'cockroach', 'bug', 'insects',
    'macchar', 'mosquito', 'chuha', 'rat', 'pest control', 'spray',
    'dabbe maar', 'keetnashak',
  ],
  'home cleaning': [
    'ghar saaf', 'poora ghar', 'full home', 'full house', 'complete cleaning',
    'deep clean', 'move in', 'move out',
  ],
}

/**
 * Urgency keyword patterns (Hindi + English + Hinglish).
 */
const URGENCY_KEYWORDS = [
  'jaldi', 'जल्दी', 'abhi', 'अभी', 'urgent', 'emergency', 'turant',
  'तुरंत', 'abhi karo', 'right now', 'immediately', 'bahut jaldi',
  'bahut zaruri', 'zaruri', 'kal subah tak', 'aaj hi',
]

/**
 * Extracts a service booking intent from a voice transcript.
 *
 * @param {string} transcript - Raw text from Web Speech API (Hindi/Hinglish)
 * @returns {{ service_type: string|null, urgency: 'URGENT'|'NORMAL', confidence: number }}
 */
export function extractBookingIntent(transcript) {
  if (!transcript || transcript.trim().length === 0) {
    return { service_type: null, urgency: 'NORMAL', confidence: 0 }
  }

  const raw = transcript.toLowerCase().trim()

  // Detect urgency first
  const urgency = URGENCY_KEYWORDS.some(kw => raw.includes(kw.toLowerCase()))
    ? 'URGENT'
    : 'NORMAL'

  let bestService = null
  let bestScore = 0

  for (const [serviceName, keywords] of Object.entries(SERVICE_MAP)) {
    let score = 0
    let matchCount = 0

    for (const kw of keywords) {
      const kwLower = kw.toLowerCase()

      // Direct inclusion check (Devanagari works too since includes() is Unicode-aware)
      if (raw.includes(kwLower)) {
        score += kwLower.length >= 5 ? 3 : 2  // longer keyword = stronger signal
        matchCount++
        continue
      }

      // Fuzzy phonetic match on individual words
      const words = raw.split(/\s+/)
      for (const word of words) {
        const dist = levenshteinDistance(phoneticNormalize(word), phoneticNormalize(kwLower))
        if (dist <= 1 && word.length > 2) {
          score += 1
          matchCount++
          break
        }
      }
    }

    if (score > bestScore) {
      bestScore = score
      bestService = serviceName
    }
  }

  // Normalize confidence 0.0 – 1.0
  const confidence = bestScore > 0
    ? Math.min(bestScore / 6, 1.0)
    : 0

  // Capitalize service name to match DB format
  const serviceTypeFormatted = bestService
    ? bestService.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
    : null

  return {
    service_type: confidence >= 0.3 ? serviceTypeFormatted : null,
    urgency,
    confidence: parseFloat(confidence.toFixed(2)),
  }
}
