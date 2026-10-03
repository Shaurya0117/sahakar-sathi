import { describe, it, expect } from 'vitest'
import { parseConfirmation } from './parseConfirmation'

describe('parseConfirmation', () => {
  it('identifies English yes', () => {
    expect(parseConfirmation('yes')).toBe('yes')
    expect(parseConfirmation('YES please')).toBe('yes')
  })
  it('identifies English no', () => {
    expect(parseConfirmation('no thanks')).toBe('no')
    expect(parseConfirmation('cancel it')).toBe('no')
    expect(parseConfirmation('that is wrong')).toBe('no')
  })
  it('identifies Hindi yes', () => {
    expect(parseConfirmation('haan')).toBe('yes')
    expect(parseConfirmation('हाँ')).toBe('yes')
    expect(parseConfirmation('theek')).toBe('yes')
    expect(parseConfirmation('theek hai')).toBe('yes')
    expect(parseConfirmation('karo')).toBe('yes')
  })
  it('identifies Hindi no', () => {
    expect(parseConfirmation('nahi')).toBe('no')
    expect(parseConfirmation('नहीं')).toBe('no')
    expect(parseConfirmation('mat karo')).toBe('no')
    expect(parseConfirmation('ruko')).toBe('no')
    expect(parseConfirmation('karo mat')).toBe('no')
  })
  it('prioritizes no over yes', () => {
    expect(parseConfirmation('that is wrong mat karo')).toBe('no')
    expect(parseConfirmation('नहीं मत करो')).toBe('no')
    expect(parseConfirmation('yes but wait ruko')).toBe('no')
    expect(parseConfirmation('theek nahi')).toBe('no')
  })
  it('identifies unclear', () => {
    expect(parseConfirmation('hello')).toBe('unclear')
    expect(parseConfirmation('that')).toBe('unclear')
    expect(parseConfirmation('kya')).toBe('unclear')
  })
  it('handles punctuation correctly', () => {
    expect(parseConfirmation('yes, absolutely')).toBe('yes')
    expect(parseConfirmation('mat karo!')).toBe('no')
    expect(parseConfirmation('नहीं।')).toBe('no')
  })
  it('handles casing correctly', () => {
    expect(parseConfirmation('NO')).toBe('no')
    expect(parseConfirmation('yEs')).toBe('yes')
    expect(parseConfirmation('mAT KaRo')).toBe('no')
  })
  it('handles spaces properly', () => {
    expect(parseConfirmation('  yes  ')).toBe('yes')
    expect(parseConfirmation('    nahi    ')).toBe('no')
  })
  it('does not match partial English words as Hindi words', () => {
    expect(parseConfirmation('that is fine')).toBe('unclear') // that has ha, but is not haan/ha
    expect(parseConfirmation('carol')).toBe('unclear') // has karo
    expect(parseConfirmation('nautical')).toBe('unclear') // has na
  })
  it('does not match partial Hindi words', () => {
    expect(parseConfirmation('bahaana')).toBe('unclear') // has haan
  })
})

