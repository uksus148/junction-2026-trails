// Reference day planner. Backend ports this 1:1 (see CLAUDE.md), so keep it pure and dependency-free.
import type { DayPlan, DropReason, DroppedPlace, ItineraryStop, LatLon, Place, Preferences, ReplanRequest, TravelMode } from '../types'
import { haversineKm, TRAIL_WINDING_FACTOR } from './geo'
import { filterAndScore, PACE_PROFILES, type ScoredPlace } from './preferences'
import { fromMinutes, toMinutes } from './time'

const TRANSIT_THRESHOLD_KM = 2.5 // longer legs are done by public transport
const TRANSIT_KMH = 18
const TRANSIT_WAIT_MIN = 8
const DEFAULT_DWELL_MIN = 45
const END_OF_DAY_MIN = 24 * 60

type Leg = { km: number; travelMin: number; mode: TravelMode }

type Visit = { scored: ScoredPlace; leg: Leg; startMin: number; leaveMin: number; problem: DropReason | null }

type ScheduleState = { position: LatLon; timeMin: number; walkedKm: number; remaining: ScoredPlace[]; stops: ItineraryStop[] }

type ScheduleInput = { from: LatLon; startMin: number; endMin: number; pool: Place[]; prefs: Preferences; walkedKm: number }

type ScheduleResult = { stops: ItineraryStop[]; dropped: DroppedPlace[]; walkKm: number }

const round1 = (n: number) => Math.round(n * 10) / 10

export function legBetween(from: LatLon, to: LatLon, prefs: Preferences): Leg {
  const km = haversineKm(from, to) * TRAIL_WINDING_FACTOR
  if (km > TRANSIT_THRESHOLD_KM) {
    return { km, mode: 'transit', travelMin: Math.round((km / TRANSIT_KMH) * 60 + TRANSIT_WAIT_MIN) }
  }
  return { km, mode: 'walk', travelMin: Math.round((km / PACE_PROFILES[prefs.pace].walkKmh) * 60) }
}

const dwellOf = (place: Place, prefs: Preferences) =>
  Math.round((place.dwellMin ?? DEFAULT_DWELL_MIN) * PACE_PROFILES[prefs.pace].dwellFactor)

function evaluate(scored: ScoredPlace, state: ScheduleState, input: ScheduleInput): Visit {
  const { place } = scored
  const leg = legBetween(state.position, place, input.prefs)
  const opens = place.openingHours ? toMinutes(place.openingHours.open) : 0
  const closes = place.openingHours ? toMinutes(place.openingHours.close) : END_OF_DAY_MIN
  const startMin = Math.max(state.timeMin + leg.travelMin, opens)
  const leaveMin = startMin + dwellOf(place, input.prefs)
  const overWalk = leg.mode === 'walk' && state.walkedKm + leg.km > input.prefs.maxWalkKm
  const problem: DropReason | null = leaveMin > closes ? 'closed' : leaveMin > input.endMin ? 'no_time' : overWalk ? 'walk_limit' : null
  return { scored, leg, startMin, leaveMin, problem }
}

/** Best value for time: score per minute spent getting there, waiting and visiting. */
function pickBest(visits: Visit[], nowMin: number): Visit | undefined {
  const value = (v: Visit) => v.scored.score / Math.max(1, v.leaveMin - nowMin)
  return visits.reduce<Visit | undefined>((best, v) => (!best || value(v) > value(best) ? v : best), undefined)
}

function advance(state: ScheduleState, visit: Visit): ScheduleState {
  const stop: ItineraryStop = {
    place: visit.scored.place,
    arriveAt: fromMinutes(visit.startMin),
    leaveAt: fromMinutes(visit.leaveMin),
    travelMin: visit.leg.travelMin,
    travelKm: round1(visit.leg.km),
    travelMode: visit.leg.mode,
    status: 'planned',
  }
  return {
    position: visit.scored.place,
    timeMin: visit.leaveMin,
    walkedKm: state.walkedKm + (visit.leg.mode === 'walk' ? visit.leg.km : 0),
    remaining: state.remaining.filter((s) => s !== visit.scored),
    stops: [...state.stops, stop],
  }
}

/** From the given state, keep taking the best next place that still fits. Returns the final state and why the rest didn't fit. */
function greedy(initial: ScheduleState, input: ScheduleInput): { state: ScheduleState; leftOver: DroppedPlace[] } {
  let state = initial
  for (;;) {
    const visits = state.remaining.map((s) => evaluate(s, state, input))
    const best = pickBest(
      visits.filter((v) => v.problem === null),
      state.timeMin,
    )
    if (!best) return { state, leftOver: visits.map((v) => ({ place: v.scored.place, reason: v.problem ?? 'no_time' })) }
    state = advance(state, best)
  }
}

/** Visit places in exactly this order; null if any of them no longer fits. */
function simulate(order: ScoredPlace[], initial: ScheduleState, input: ScheduleInput): ScheduleState | null {
  let state = initial
  for (const scored of order) {
    const visit = evaluate(scored, state, input)
    if (visit.problem) return null
    state = advance(state, visit)
  }
  return state
}

const travelTime = (state: ScheduleState) => state.stops.reduce((sum, s) => sum + s.travelMin, 0)

/** 2-opt: reverse parts of the visiting order while that cuts travel time and every stop still fits. */
function improveOrder(chosen: ScheduleState, initial: ScheduleState, input: ScheduleInput): ScheduleState {
  const scoredOf = new Map(initial.remaining.map((s) => [s.place.id, s]))
  let order = chosen.stops.map((s) => scoredOf.get(s.place.id)!)
  let best = chosen
  for (let improved = true; improved; ) {
    improved = false
    for (let i = 0; i < order.length - 1 && !improved; i++) {
      for (let j = i + 1; j < order.length && !improved; j++) {
        const candidate = [...order.slice(0, i), ...order.slice(i, j + 1).reverse(), ...order.slice(j + 1)]
        const result = simulate(candidate, initial, input)
        if (result && travelTime(result) < travelTime(best)) {
          order = candidate
          best = result
          improved = true
        }
      }
    }
  }
  return best
}

/** Pick what to visit greedily, tidy the order, then use any time that frees up. */
function schedule(input: ScheduleInput): ScheduleResult {
  const { scored, dropped } = filterAndScore(input.pool, input.prefs)
  const initial: ScheduleState = { position: input.from, timeMin: input.startMin, walkedKm: input.walkedKm, remaining: scored, stops: [] }
  const first = greedy(initial, input)
  const reordered = improveOrder(first.state, initial, input)
  const final = reordered === first.state ? first : greedy(reordered, input)
  return { stops: final.state.stops, dropped: [...dropped, ...final.leftOver], walkKm: round1(final.state.walkedKm) }
}

export type DayPlanInput = Pick<DayPlan, 'start' | 'startTime' | 'endTime' | 'candidates' | 'preferences'>

export function planDay(input: DayPlanInput): DayPlan {
  const result = schedule({
    from: input.start,
    startMin: toMinutes(input.startTime),
    endMin: toMinutes(input.endTime),
    pool: input.candidates,
    prefs: input.preferences,
    walkedKm: 0,
  })
  return { ...input, ...result, resumeAt: input.startTime }
}

/** Re-plan the rest of the day: done stops stay, skipped places are excluded for good, the rest is rescheduled from `now`. */
export function replanDay(plan: DayPlan, request: ReplanRequest): DayPlan {
  const doneIds = new Set([...request.donePlaceIds, ...plan.stops.filter((s) => s.status === 'done').map((s) => s.place.id)])
  const skippedIds = new Set([
    ...request.skipPlaceIds,
    ...plan.dropped.filter((d) => d.reason === 'skipped_by_user').map((d) => d.place.id),
  ])
  const done = plan.stops.filter((s) => doneIds.has(s.place.id)).map((s) => ({ ...s, status: 'done' as const }))
  const preferences = request.preferences ?? plan.preferences
  const result = schedule({
    from: request.location ?? done.at(-1)?.place ?? plan.start,
    startMin: toMinutes(request.now),
    endMin: toMinutes(plan.endTime),
    pool: plan.candidates.filter((p) => !doneIds.has(p.id) && !skippedIds.has(p.id)),
    prefs: preferences,
    walkedKm: done.filter((s) => s.travelMode === 'walk').reduce((sum, s) => sum + s.travelKm, 0),
  })
  const skipped = plan.candidates
    .filter((p) => skippedIds.has(p.id) && !doneIds.has(p.id))
    .map((place) => ({ place, reason: 'skipped_by_user' as const }))
  return {
    ...plan,
    preferences,
    stops: [...done, ...result.stops],
    dropped: [...skipped, ...result.dropped],
    walkKm: result.walkKm,
    resumeAt: request.now,
  }
}
