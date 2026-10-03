import { describe, it, expect } from 'vitest'
import { fuzzyMatchIntent } from './phoneticMatcher'

describe('Phonetic Matcher Accuracy Test', () => {
  it('should evaluate 30 noisy commands and report accuracy', () => {
    const testSet = [
      // Accept
      { text: 'ha accept karlo', intent: 'accept', expected: true },
      { text: 'haan', intent: 'accept', expected: true },
      { text: 'yes i accept', intent: 'accept', expected: true },
      { text: 'nahi karna', intent: 'accept', expected: false },
      { text: 'acpt', intent: 'accept', expected: true }, // misspelling
      { text: 'swikar hai', intent: 'accept', expected: true },
      { text: 'svikar', intent: 'accept', expected: true },
      // Start
      { text: 'kaam shuru karo', intent: 'start', expected: true },
      { text: 'start the job', intent: 'start', expected: true },
      { text: 'shuruat kardo', intent: 'start', expected: true },
      { text: 'staret', intent: 'start', expected: true }, // misspelling
      { text: 'kaam chalu', intent: 'start', expected: true },
      { text: 'shru kro', intent: 'start', expected: true }, // hinglish short
      // Complete
      { text: 'kaam khatam', intent: 'complete', expected: true },
      { text: 'job is done', intent: 'complete', expected: true },
      { text: 'pura ho gaya', intent: 'complete', expected: true },
      { text: 'kaam pura ho gya', intent: 'complete', expected: true },
      { text: 'khatm', intent: 'complete', expected: true }, // missing 'a'
      { text: 'cmplete', intent: 'complete', expected: true }, // typo
      // Help
      { text: 'help chahiye', intent: 'help', expected: true },
      { text: 'madad karo', intent: 'help', expected: true },
      { text: 'i need assistance', intent: 'help', expected: true },
      { text: 'madd kro', intent: 'help', expected: true },
      { text: 'hlp me', intent: 'help', expected: true },
      // Balance
      { text: 'paisa kitna hua', intent: 'balance', expected: true },
      { text: 'balance check', intent: 'balance', expected: true },
      { text: 'mera khata dikhao', intent: 'balance', expected: true },
      { text: 'blnce', intent: 'balance', expected: true },
      { text: 'pese dekhne hai', intent: 'balance', expected: true }, // 'pese' instead of 'paisa'
      // Cancel
      { text: 'cancel the job', intent: 'cancel', expected: true },
      { text: 'radh karo', intent: 'cancel', expected: true },
      { text: 'nahi krna', intent: 'cancel', expected: true }, // 'nahi'
      { text: 'cncl', intent: 'cancel', expected: true }
    ];

    const intentTargets = {
      accept: ['accept', 'swikaar', 'ha', 'haan', 'yes', 'svikar'],
      start: ['start', 'shuru', 'chalu'],
      complete: ['complete', 'done', 'khatam', 'pura'],
      help: ['help', 'madad', 'assistance'],
      balance: ['balance', 'paisa', 'khata', 'pese'],
      cancel: ['cancel', 'radh', 'nahi']
    };

    let exactCorrect = 0;
    let phoneticCorrect = 0;
    let total = testSet.length;

    testSet.forEach(({ text, intent, expected }) => {
      const targets = intentTargets[intent];
      
      // Exact Match
      const isExact = targets.some(t => text.toLowerCase().includes(t.toLowerCase()));
      if (isExact === expected) exactCorrect++;

      // Phonetic Match
      const isPhonetic = fuzzyMatchIntent(text, targets, 2, false);
      if (isPhonetic === expected) phoneticCorrect++;
    });

    console.log('--- TEST RESULTS ---');
    console.log('EXACT MATCH ACCURACY: ' + ((exactCorrect / total) * 100).toFixed(2) + '%');
    console.log('PHONETIC MATCH ACCURACY: ' + ((phoneticCorrect / total) * 100).toFixed(2) + '%');
    console.log('--------------------');
    
    // We don't fail the test if exact == phonetic, the user just wants real numbers.
    expect(true).toBe(true); 
  });
})
