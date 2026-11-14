import { describe, expect, it } from 'vitest'
import { formatAscent, formatDistance, formatDuration } from './format'

describe('formatDistance', () => {
  it('rounds live API kilometres to one decimal', () => {
    expect(formatDistance(15.178600000000001)).toBe('15.2 km')
  })

  it('drops a trailing zero for whole kilometres', () => {
    expect(formatDistance(9)).toBe('9 km')
  })

  it('shows a dash for a negative or non-finite distance', () => {
    expect(formatDistance(-1)).toBe('—')
    expect(formatDistance(Number.NaN)).toBe('—')
  })
})

describe('formatAscent', () => {
  it('rounds metres to a whole number', () => {
    expect(formatAscent(746.01)).toBe('746 m')
  })

  it('shows a dash when there is no ascent', () => {
    expect(formatAscent(0)).toBe('—')
    expect(formatAscent(0.4)).toBe('—')
  })
})

describe('formatDuration', () => {
  it('rounds fractional minutes before splitting into hours', () => {
    expect(formatDuration(302.015)).toBe('5h 02m')
  })

  it('carries 59.6 minutes over to a full hour', () => {
    expect(formatDuration(59.6)).toBe('1h 00m')
  })

  it('keeps whole-minute mock values unchanged', () => {
    expect(formatDuration(120)).toBe('2h 00m')
  })

  it('shows a dash for a negative or non-finite duration', () => {
    expect(formatDuration(-5)).toBe('—')
    expect(formatDuration(Number.POSITIVE_INFINITY)).toBe('—')
  })
})
