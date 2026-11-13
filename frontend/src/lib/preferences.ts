import type { Budget, DropReason, DroppedPlace, Pace, Place, Preferences } from '../types'

export const PLACE_TAGS = ['castle', 'museum', 'church', 'viewpoint', 'nature', 'waterfall', 'lake', 'peak', 'oldtown'] as const

const PACES: Pace[] = ['relaxed', 'normal', 'intense']
const BUDGETS: Budget[] = [0, 1, 2, 3]
const MAX_WALK_KM_LIMIT = 100

export const DEFAULT_PREFERENCES: Preferences = {
  interests: [],
  dislikes: [],
  pace: 'normal',
  maxWalkKm: 12,
  budget: 3,
  avoidCrowds: false,
}

/** How fast the user walks and how long they like to stay at a place. */
export const PACE_PROFILES: Record<Pace, { walkKmh: number; dwellFactor: number }> = {
  relaxed: { walkKmh: 3.5, dwellFactor: 1.3 },
  normal: { walkKmh: 4.5, dwellFactor: 1 },
  intense: { walkKmh: 5.5, dwellFactor: 0.75 },
}

const BASE_SCORE = 1
const INTEREST_BONUS = 2
const CROWD_PENALTY = 0.4
const MIN_SCORE = 0.1

export type ScoredPlace = { place: Place; score: number }

function exclusionReason(place: Place, prefs: Preferences): DropReason | null {
  if (place.tags.some((tag) => prefs.dislikes.includes(tag))) return 'dislike'
  if ((place.priceLevel ?? 0) > prefs.budget) return 'budget'
  return null
}

function scoreOf(place: Place, prefs: Preferences): number {
  const matches = place.tags.filter((tag) => prefs.interests.includes(tag)).length
  const crowdPenalty = prefs.avoidCrowds ? CROWD_PENALTY * (place.crowdLevel ?? 0) : 0
  return Math.max(MIN_SCORE, BASE_SCORE + INTEREST_BONUS * matches - crowdPenalty)
}

/** Remove places the user would not want and rank the rest by how well they fit. */
export function filterAndScore(places: Place[], prefs: Preferences): { scored: ScoredPlace[]; dropped: DroppedPlace[] } {
  return places.reduce<{ scored: ScoredPlace[]; dropped: DroppedPlace[] }>(
    (acc, place) => {
      const reason = exclusionReason(place, prefs)
      return reason
        ? { ...acc, dropped: [...acc.dropped, { place, reason }] }
        : { ...acc, scored: [...acc.scored, { place, score: scoreOf(place, prefs) }] }
    },
    { scored: [], dropped: [] },
  )
}

const unique = (items: string[]) => [...new Set(items)]

/** Apply what the user just said on top of the saved profile. A tag can't be liked and disliked at once. */
export function mergePreferences(prefs: Preferences, patch: Partial<Preferences>): Preferences {
  const newLikes = patch.interests ?? []
  const newDislikes = patch.dislikes ?? []
  return {
    ...prefs,
    ...patch,
    interests: unique([...prefs.interests.filter((t) => !newDislikes.includes(t)), ...newLikes]),
    dislikes: unique([...prefs.dislikes.filter((t) => !newLikes.includes(t)), ...newDislikes]),
  }
}

const stringArray = (value: unknown): string[] => (Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [])

/** Read preferences saved in the browser; anything malformed falls back to defaults. */
export function parseStoredPreferences(raw: string | null): Preferences {
  if (!raw) return DEFAULT_PREFERENCES
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return DEFAULT_PREFERENCES
  }
  if (typeof data !== 'object' || data === null) return DEFAULT_PREFERENCES
  const d = data as Record<string, unknown>
  const walk = d.maxWalkKm
  return {
    interests: stringArray(d.interests),
    dislikes: stringArray(d.dislikes),
    pace: PACES.includes(d.pace as Pace) ? (d.pace as Pace) : DEFAULT_PREFERENCES.pace,
    maxWalkKm: typeof walk === 'number' && walk > 0 && walk <= MAX_WALK_KM_LIMIT ? walk : DEFAULT_PREFERENCES.maxWalkKm,
    budget: BUDGETS.includes(d.budget as Budget) ? (d.budget as Budget) : DEFAULT_PREFERENCES.budget,
    avoidCrowds: typeof d.avoidCrowds === 'boolean' ? d.avoidCrowds : DEFAULT_PREFERENCES.avoidCrowds,
  }
}
