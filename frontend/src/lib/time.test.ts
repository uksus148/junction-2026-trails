import { describe, expect, it } from 'vitest'
import { addMinutes, fromMinutes, isValidTime, toMinutes } from './time'

describe('time helpers', () => {
  it('converts between HH:MM and minutes', () => {
    expect(toMinutes('09:30')).toBe(570)
    expect(fromMinutes(570)).toBe('09:30')
  })

  it('clamps results to a single day', () => {
    expect(fromMinutes(-5)).toBe('00:00')
    expect(fromMinutes(24 * 60 + 10)).toBe('23:59')
  })

  it('adds minutes across an hour boundary', () => {
    expect(addMinutes('10:45', 30)).toBe('11:15')
  })

  it('validates time strings', () => {
    expect(isValidTime('23:59')).toBe(true)
    expect(isValidTime('24:00')).toBe(false)
    expect(isValidTime('')).toBe(false)
  })

  it('rejects malformed input', () => {
    expect(() => toMinutes('9am')).toThrow('Invalid time')
  })
})
