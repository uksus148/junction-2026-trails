import type { Place } from '../types'
import { safeUrl } from './errors'

/** The place's source as a safe link, or null for manual places and anything that is not http(s). */
export function sourceLink(place: Place): string | null {
  return safeUrl(place.source) ?? null
}

/**
 * Chat places the route does not list. A route's `places` are its intermediate stops,
 * so for a chat route these are the start and finish places, in chat order.
 */
export function contextPlaces(routePlaces: Place[], chatPlaces: Place[]): Place[] {
  return mergePlaces(routePlaces, chatPlaces).slice(routePlaces.length)
}

/** Add places from a chat reply to the ones already chosen, keeping order and skipping duplicates by id. */
export function mergePlaces(current: Place[], incoming: Place[]): Place[] {
  const known = new Set(current.map((p) => p.id))
  return [...current, ...incoming.filter((p) => !known.has(p.id))]
}
