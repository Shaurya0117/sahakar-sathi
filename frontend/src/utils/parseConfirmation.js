export function parseConfirmation(text) {
  const normalized = text.toLowerCase().trim();
  
  // Negative targets first
  const negativeWords = ['no', 'na', 'nahi', 'नहीं', 'mat karo', 'ruko', 'cancel'];
  for (const word of negativeWords) {
    if (new RegExp('\\b' + word + '\\b').test(normalized)) {
      return 'no';
    }
  }

  // Positive targets second
  const positiveWords = ['yes', 'haan', 'ha', 'theek', 'karo', 'हाँ'];
  for (const word of positiveWords) {
    if (new RegExp('\\b' + word + '\\b').test(normalized)) {
      return 'yes';
    }
  }

  return 'unclear';
}
