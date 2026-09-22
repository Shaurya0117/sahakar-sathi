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
 * Very basic Soundex-style phonetic normalization for Hindi/English variations.
 * Strips vowels and groups similar sounding consonants.
 */
function phoneticNormalize(str) {
  if (!str) return ''
  let s = str.toLowerCase().replace(/[^a-z0-9\s]/g, '')
  
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
export function fuzzyMatchIntent(transcript, targetPhrases, threshold = 2) {
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
        // Phonetic Levenshtein (e.g. "kamaai" vs "kamayee")
        if (levenshteinDistance(phoneticNormalize(pw), phoneticNormalize(tw)) <= 1) {
          wordMatched = true
          break
        }
      }
      if (wordMatched) matchedWords++
    }
    
    // If we matched at least 70% of the words in the target phrase, consider it a match
    if (phraseWords.length > 0 && matchedWords / phraseWords.length >= 0.7) {
      return true
    }
  }
  
  return false
}
