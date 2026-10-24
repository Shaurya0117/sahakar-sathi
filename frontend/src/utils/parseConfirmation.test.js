import { describe, it, expect } from 'vitest'
import { parseConfirmation } from './parseConfirmation'

describe('parseConfirmation', () => {
  it('identifies English yes', () => { expect(parseConfirmation('yes please')).toBe('yes') })
  it('identifies English no', () => { expect(parseConfirmation('no thanks')).toBe('no') })
  it('identifies Hindi yes', () => { expect(parseConfirmation('haan')).toBe('yes') })
  it('identifies Hindi no', () => { expect(parseConfirmation('nahi')).toBe('no') })
  it('prioritizes no over yes', () => { expect(parseConfirmation('yes but no')).toBe('no') })
  it('identifies unclear', () => { expect(parseConfirmation('maybe')).toBe('unclear') })
  it('handles punctuation', () => { expect(parseConfirmation('haan, zaroor!')).toBe('yes') })
  it('handles casing', () => { expect(parseConfirmation('NaHi')).toBe('no') })
  it('handles spaces', () => { expect(parseConfirmation('  yes  ')).toBe('yes') })
  it('does not match partial English', () => { expect(parseConfirmation('nosh')).toBe('unclear') })
  it('does not match partial Hindi', () => { expect(parseConfirmation('karon')).toBe('unclear') })
  
  // Devanagari tests
  it('identifies Devanagari haan', () => { expect(parseConfirmation('हाँ')).toBe('yes') })
  it('identifies Devanagari ha', () => { expect(parseConfirmation('हां')).toBe('yes') })
  it('identifies Devanagari nahi', () => { expect(parseConfirmation('नहीं')).toBe('no') })
  it('identifies Devanagari nahi without dot', () => { expect(parseConfirmation('नही')).toBe('no') })
  it('identifies Devanagari mat karo', () => { expect(parseConfirmation('यह मत करो')).toBe('no') })
  it('identifies Devanagari karo', () => { expect(parseConfirmation('शुरू करो')).toBe('yes') })
})
