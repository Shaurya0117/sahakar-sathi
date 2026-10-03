import { describe, it, expect } from 'vitest'
import { fuzzyMatchIntent } from './phoneticMatcher'

describe('Phonetic Matcher Accuracy Test', () => {
  it('should evaluate 20 commands and report accuracy', () => {
    const testSet = [
      { text: 'हाँ, काम स्वीकार करो', intent: 'accept', expected: true },
      { text: 'ha accept karlo', intent: 'accept', expected: true },
      { text: 'haan', intent: 'accept', expected: true },
      { text: 'yes i accept', intent: 'accept', expected: true },
      { text: 'nahi karna', intent: 'accept', expected: false },
      { text: 'kaam shuru karo', intent: 'start', expected: true },
      { text: 'start the job', intent: 'start', expected: true },
      { text: 'shuruat kardo', intent: 'start', expected: true },
      { text: 'kaam khatam', intent: 'complete', expected: true },
      { text: 'job is done', intent: 'complete', expected: true },
      { text: 'pura ho gaya', intent: 'complete', expected: true },
      { text: 'kaam pura ho gya', intent: 'complete', expected: true },
      { text: 'help chahiye', intent: 'help', expected: true },
      { text: 'madad karo', intent: 'help', expected: true },
      { text: 'i need assistance', intent: 'help', expected: true },
      { text: 'paisa kitna hua', intent: 'balance', expected: true },
      { text: 'balance check', intent: 'balance', expected: true },
      { text: 'mera khata dikhao', intent: 'balance', expected: true },
      { text: 'cancel the job', intent: 'cancel', expected: true },
      { text: 'radh karo', intent: 'cancel', expected: true }
    ];

    const intentTargets = {
      accept: ['accept', 'swikaar', 'ha', 'haan', 'yes'],
      start: ['start', 'shuru', 'chalu'],
      complete: ['complete', 'done', 'khatam', 'pura'],
      help: ['help', 'madad', 'assistance'],
      balance: ['balance', 'paisa', 'khata'],
      cancel: ['cancel', 'radh', 'nahi']
    };

    let exactCorrect = 0;
    let phoneticCorrect = 0;

    testSet.forEach(({ text, intent, expected }) => {
      const targets = intentTargets[intent];
      
      // Exact Match
      const isExact = targets.some(t => text.toLowerCase().includes(t.toLowerCase()));
      if (isExact === expected) exactCorrect++;

      // Phonetic Match
      const isPhonetic = fuzzyMatchIntent(text, targets, 2, false);
      if (isPhonetic === expected) phoneticCorrect++;
    });

    console.log('EXACT MATCH ACCURACY: ' + ((exactCorrect / 20) * 100) + '%');
    console.log('PHONETIC MATCH ACCURACY: ' + ((phoneticCorrect / 20) * 100) + '%');
    
    expect(phoneticCorrect).toBeGreaterThanOrEqual(18); // expect >= 90%
  });
})
