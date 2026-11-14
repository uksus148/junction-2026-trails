import { describe, expect, it } from 'vitest'
import type { Place } from '../types'
import { DEFAULT_PREFERENCES, filterAndScore, mergePreferences, parseStoredPreferences } from './preferences'

const place = (id: string, overrides: Partial<Place> = {}): Place => ({
  id,
  name: id,
  lat: 0,
  lon: 0,
  tags: ['viewpoint'],
  photos: [],
  source: 'test',
  ...overrides,
})

describe('filterAndScore', () => {
  it('drops disliked tags and places over budget', () => {
    const { scored, dropped } = filterAndScore([place('m', { tags: ['museum'] }), place('p', { priceLevel: 2 }), place('ok')], {
      ...DEFAULT_PREFERENCES,
      dislikes: ['museum'],
      budget: 1,
    })

    expect(scored.map((s) => s.place.id)).toEqual(['ok'])
    expect(dropped.map((d) => [d.place.id, d.reason])).toEqual([
      ['m', 'dislike'],
      ['p', 'budget'],
    ])
  })

  it('scores interest matches higher', () => {
    const { scored } = filterAndScore([place('plain'), place('castle', { tags: ['castle'] })], { ...DEFAULT_PREFERENCES, interests: ['castle'] })
    const score = (id: string) => scored.find((s) => s.place.id === id)!.score

    expect(score('castle')).toBeGreaterThan(score('plain'))
  })

  it('penalises crowded places only when the user avoids crowds', () => {
    const places = [place('quiet', { crowdLevel: 0 }), place('busy', { crowdLevel: 2 })]
    const avoid = filterAndScore(places, { ...DEFAULT_PREFERENCES, avoidCrowds: true }).scored
    const relaxed = filterAndScore(places, DEFAULT_PREFERENCES).scored

    expect(avoid[1].score).toBeLessThan(avoid[0].score)
    expect(relaxed[1].score).toBe(relaxed[0].score)
  })
})

describe('mergePreferences', () => {
  it('moves a tag from interests to dislikes without duplicates', () => {
    const merged = mergePreferences({ ...DEFAULT_PREFERENCES, interests: ['museum', 'castle'] }, { dislikes: ['museum'], pace: 'relaxed' })

    expect(merged.interests).toEqual(['castle'])
    expect(merged.dislikes).toEqual(['museum'])
    expect(merged.pace).toBe('relaxed')
  })
})

describe('parseStoredPreferences', () => {
  it('falls back to defaults for broken or foreign data', () => {
    expect(parseStoredPreferences('not json')).toEqual(DEFAULT_PREFERENCES)
    expect(parseStoredPreferences(JSON.stringify({ pace: 'warp', maxWalkKm: -5, interests: [1, 'castle'] }))).toEqual({
      ...DEFAULT_PREFERENCES,
      interests: ['castle'],
    })
  })
})
