import { describe, expect, it } from 'vitest'
import { boundsOf, haversineKm, round1, sliceLineByFraction } from './geo'

describe('geo helpers', () => {
  it('measures great-circle distance', () => {
    const strbskePleso = { lat: 49.1191, lon: 20.0627 }
    const rysy = { lat: 49.1795, lon: 20.088 }

    const km = haversineKm(strbskePleso, rysy)

    expect(km).toBeGreaterThan(6.8)
    expect(km).toBeLessThan(7.1)
  })

  it('cuts a line between two fractions of its length', () => {
    const line: [number, number][] = [
      [0, 0],
      [0, 1],
      [0, 2],
    ]

    expect(sliceLineByFraction(line, 0, 0.5)).toEqual([
      [0, 0],
      [0, 1],
    ])
  })

  it('returns the bounding box as [south-west, north-east]', () => {
    expect(
      boundsOf([
        [1, 2],
        [3, 0],
      ]),
    ).toEqual([
      [1, 0],
      [3, 2],
    ])
  })

  it('rounds kilometres to one decimal', () => {
    expect(round1(2.34)).toBe(2.3)
  })
})
