import type { LatLon, Place, Route } from '../types'
import { safeUrl } from './errors'

/** The place's source as a safe link, or null for manual places and anything that is not http(s). */
export function sourceLink(place: Place): string | null {
  return safeUrl(place.source) ?? null
}

/** How to describe a place's provenance: only `source: "manual"` means it was added by hand. */
export function sourceKind(place: Place): 'link' | 'manual' | 'unavailable' {
  if (sourceLink(place)) return 'link'
  return place.source === 'manual' ? 'manual' : 'unavailable'
}

/**
 * Chat places the route does not list. A route's `places` are its intermediate stops,
 * so for a chat route these are the start and finish places, in chat order.
 */
/** One entry per place id, in first-occurrence order (repeated visits get one marker). */
export function uniqueById(places: Place[]): Place[] {
  return places.filter((place, index) => places.findIndex((p) => p.id === place.id) === index)
}

export type RouteEndpoint = { point: LatLon; place?: Place }

const trackPoint = (coordinate: [number, number] | undefined): LatLon | null =>
  coordinate ? { lat: coordinate[1], lon: coordinate[0] } : null

/**
 * A and B sit on the track's first and last coordinates (the router may snap them away from the stored places).
 * The chat's start/finish places, which the route does not list (D3/D5), supply name and source only.
 */
export function routeEndpoints(route: Route, chatPlaces: Place[]): { start: RouteEndpoint | null; end: RouteEndpoint | null } {
  const extra = contextPlaces(route.places, chatPlaces)
  const startPlace = extra.find((p) => p.id === chatPlaces[0]?.id)
  const endPlace = extra.find((p) => p.id === chatPlaces.at(-1)?.id && p.id !== startPlace?.id)
  const startPoint = trackPoint(route.geojson.coordinates[0])
  const endPoint = trackPoint(route.geojson.coordinates.at(-1))
  return {
    start: startPoint && { point: startPoint, ...(startPlace && { place: startPlace }) },
    end: endPoint && { point: endPoint, ...(endPlace && { place: endPlace }) },
  }
}

export function contextPlaces(routePlaces: Place[], chatPlaces: Place[]): Place[] {
  return mergePlaces(routePlaces, chatPlaces).slice(routePlaces.length)
}

/** Add places from a chat reply to the ones already chosen, keeping order and skipping duplicates by id. */
export function mergePlaces(current: Place[], incoming: Place[]): Place[] {
  const known = new Set(current.map((p) => p.id))
  return [...current, ...incoming.filter((p) => !known.has(p.id))]
}
