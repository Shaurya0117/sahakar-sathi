export function parseConfirmation(text) {
  const normalized = text.toLowerCase().trim();
  const words = normalized.split(/[\s,?!।]+/);
  
  const negativePhrases = ["mat karo", "karo mat", "that is wrong", "मत करो"];
  for (const phrase of negativePhrases) {
    if (normalized.includes(phrase)) return "no";
  }

  const negativeWords = ["no", "na", "nahi", "नहीं", "नही", "ruko", "cancel", "wrong"];
  for (const target of negativeWords) {
    if (words.includes(target)) return "no";
  }

  const positiveWords = ["yes", "haan", "ha", "theek", "karo", "करो", "हां", "हाँ"];
  for (const target of positiveWords) {
    if (words.includes(target)) return "yes";
  }

  return "unclear";
}
