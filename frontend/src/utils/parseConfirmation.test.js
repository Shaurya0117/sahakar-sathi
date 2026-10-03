import { describe, it, expect } from 'vitest'
import { parseConfirmation } from './parseConfirmation'

describe('parseConfirmation', () => {
  it('identifies yes', () => {
    expect(parseConfirmation('yes please')).toBe('yes')
    expect(parseConfirmation('haan')).toBe('yes')
    expect(parseConfirmation('theek hai')).toBe('yes')
    expect(parseConfirmation('karo')).toBe('yes')
  })

  it('identifies no', () => {
    expect(parseConfirmation('no thanks')).toBe('no')
    expect(parseConfirmation('nahi')).toBe('no')
    expect(parseConfirmation('cancel it')).toBe('no')
  })

  it('prioritizes no over yes', () => {
    expect(parseConfirmation('mat karo')).toBe('no')
    expect(parseConfirmation('that is wrong mat karo')).toBe('no')
  })

  it('identifies unclear', () => {
    expect(parseConfirmation('hello')).toBe('unclear')
    expect(parseConfirmation('that')).toBe('unclear') // does not match ha
  })
})
