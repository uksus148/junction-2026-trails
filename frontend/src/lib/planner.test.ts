import { describe, expect, it } from 'vitest'
import type { DayPlan, Place, Preferences } from '../types'
import { planDay, replanDay } from './planner'
import { DEFAULT_PREFERENCES } from './preferences'

const START = { lat: 48.1477, lon: 17.1074 }
const STEP_DEG = 0.004 // ≈ 450 m north per step

const place = (id: string, step: number, overrides: Partial<Place> = {}): Place => ({
  id,
  name: id,
  lat: START.lat + step * STEP_DEG,
  lon: START.lon,
  tags: ['viewpoint'],
  photos: [],
  source: 'test',
  dwellMin: 60,
  ...overrides,
})

const prefs = (overrides: Partial<Preferences> = {}): Preferences => ({ ...DEFAULT_PREFERENCES, ...overrides })

const plan = (candidates: Place[], startTime = '10:00', endTime = '18:00', preferences = prefs()): DayPlan =>
  planDay({ start: START, startTime, endTime, candidates, preferences })

describe('planDay', () => {
  it('fits every stop inside the day window and drops the rest as no_time', () => {
    const result = plan([place('a', 1), place('b', 2), place('c', 3), place('d', 4), place('e', 5)], '10:00', '13:00')

    expect(result.stops.length).toBeLessThanOrEqual(3)
    expect(result.stops.every((s) => s.leaveAt <= '13:00')).toBe(true)
    expect(result.dropped.some((d) => d.reason === 'no_time')).toBe(true)
  })

  it('drops a place that is closed by the time the visitor gets there', () => {
    const result = plan([place('early', 1, { openingHours: { open: '07:00', close: '09:00' } })])

    expect(result.stops).toHaveLength(0)
    expect(result.dropped).toEqual([expect.objectContaining({ reason: 'closed' })])
  })

  it('waits for a place to open instead of arriving early', () => {
    const result = plan([place('late', 1, { openingHours: { open: '12:00', close: '17:00' } })])

    expect(result.stops[0].arriveAt).toBe('12:00')
  })

  it('never walks more than the walking limit', () => {
    // ~1.2 km walking legs; long legs would switch to transit, which doesn't count as walking
    const walkable = [place('a', 2), place('b', 4), place('c', 6)]
    const result = plan(walkable, '10:00', '18:00', prefs({ maxWalkKm: 3 }))

    expect(result.walkKm).toBeLessThanOrEqual(3)
    expect(result.dropped.some((d) => d.reason === 'walk_limit')).toBe(true)
  })

  it('excludes disliked and over-budget places with a reason', () => {
    const result = plan(
      [place('museum', 1, { tags: ['museum'] }), place('pricey', 2, { priceLevel: 3 }), place('free', 3, { priceLevel: 0 })],
      '10:00',
      '18:00',
      prefs({ dislikes: ['museum'], budget: 1 }),
    )

    expect(result.stops.map((s) => s.place.id)).toEqual(['free'])
    expect(result.dropped).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ reason: 'dislike', place: expect.objectContaining({ id: 'museum' }) }),
        expect.objectContaining({ reason: 'budget', place: expect.objectContaining({ id: 'pricey' }) }),
      ]),
    )
  })

  it('orders stops to avoid walking back and forth', () => {
    // Greedy alone grabs the favourite far one first, then walks back: start → c → b → a
    const result = plan([place('a', 1), place('b', 2), place('c', 3, { tags: ['castle'] })], '10:00', '18:00', prefs({ interests: ['castle'] }))

    expect(result.stops.map((s) => s.place.id)).toEqual(['a', 'b', 'c'])
  })

  it('prefers places matching the interests', () => {
    const result = plan([place('view', 1), place('castle', 1.2, { tags: ['castle'] })], '10:00', '11:15', prefs({ interests: ['castle'] }))

    expect(result.stops.map((s) => s.place.id)).toEqual(['castle'])
  })
})

describe('replanDay', () => {
  const day = () => plan([place('a', 1), place('b', 2), place('c', 3)], '10:00', '12:30')

  it('fills the freed time with another place after a skip', () => {
    const initial = day()
    const skippedId = initial.stops[0].place.id

    const result = replanDay(initial, { now: '10:00', skipPlaceIds: [skippedId], donePlaceIds: [] })

    expect(result.stops.map((s) => s.place.id)).not.toContain(skippedId)
    expect(result.stops).toHaveLength(initial.stops.length)
    expect(result.dropped).toEqual(expect.arrayContaining([expect.objectContaining({ reason: 'skipped_by_user' })]))
  })

  it('shifts the day when the user is running late and drops what no longer fits', () => {
    const initial = day()

    const result = replanDay(initial, { now: '11:00', skipPlaceIds: [], donePlaceIds: [] })

    expect(result.stops[0].arriveAt >= '11:00').toBe(true)
    expect(result.stops.length).toBeLessThan(initial.stops.length)
    expect(result.dropped.some((d) => d.reason === 'no_time')).toBe(true)
    expect(result.resumeAt).toBe('11:00')
  })

  it('keeps done stops unchanged', () => {
    const initial = day()
    const first = initial.stops[0]

    const result = replanDay(initial, { now: first.leaveAt, location: first.place, skipPlaceIds: [], donePlaceIds: [first.place.id] })

    expect(result.stops[0]).toEqual({ ...first, status: 'done' })
  })

  it('never replans into the time before the day starts', () => {
    const result = replanDay(day(), { now: '01:00', skipPlaceIds: [], donePlaceIds: [] })

    expect(result.stops[0].arriveAt >= '10:00').toBe(true)
    expect(result.resumeAt).toBe('10:00')
  })

  it('remembers earlier skips on the next replan', () => {
    const initial = day()
    const skippedId = initial.stops[0].place.id
    const once = replanDay(initial, { now: '10:00', skipPlaceIds: [skippedId], donePlaceIds: [] })

    const twice = replanDay(once, { now: '10:30', skipPlaceIds: [], donePlaceIds: [] })

    expect(twice.stops.map((s) => s.place.id)).not.toContain(skippedId)
  })
})
