import type { Place } from '../types'

/** Add places from a chat reply to the ones already chosen, keeping order and skipping duplicates by id. */
export function mergePlaces(current: Place[], incoming: Place[]): Place[] {
  const known = new Set(current.map((p) => p.id))
  return [...current, ...incoming.filter((p) => !known.has(p.id))]
}
