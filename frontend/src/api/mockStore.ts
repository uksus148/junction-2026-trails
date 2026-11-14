import { haversineKm, round1, TRAIL_WINDING_FACTOR } from '../lib/geo'
import type { Itinerary, LatLon, Photo, Place, Route, RouteSegment } from '../types'
import { findPhotosNear } from './wikimedia'

// Shared in-memory state for the mock backend.

export const MOCK_LATENCY_MS = 500
const WALK_KM_PER_HOUR = 4
const CLIMB_M_PER_HOUR = 600
const SAME_POINT_KM = 0.05

let placeRegistry: ReadonlyMap<string, Place> = new Map()
let routeRegistry: ReadonlyMap<string, Route> = new Map()
let itineraryRegistry: ReadonlyMap<string, Itinerary> = new Map()
let photoCache: ReadonlyMap<string, Photo[]> = new Map()

export const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
const pointKey = (p: LatLon) => `${p.lat.toFixed(4)},${p.lon.toFixed(4)}`

export async function photosNearSafe(point: LatLon): Promise<Photo[]> {
  const cached = photoCache.get(pointKey(point))
  if (cached) return cached
  try {
    const photos = await findPhotosNear(point.lat, point.lon)
    photoCache = new Map([...photoCache, [pointKey(point), photos]])
    return photos
  } catch (error) {
    console.warn('Photo lookup failed, continuing without photos', error)
    return []
  }
}

export async function withPhotos(place: Omit<Place, 'photos'>): Promise<Place> {
  return { ...place, photos: await photosNearSafe(place) }
}

export function registerPlace(place: Place): Place {
  placeRegistry = new Map([...placeRegistry, [place.id, place]])
  return place
}

export const getPlace = (id: string) => placeRegistry.get(id)

export function getRoute(id: string): Route {
  const route = routeRegistry.get(id)
  if (!route) throw new Error(`Route ${id} not found`)
  return route
}

export function saveItinerary(itinerary: Itinerary): Itinerary {
  itineraryRegistry = new Map([...itineraryRegistry, [itinerary.id, itinerary]])
  return itinerary
}

export function getItinerary(id: string): Itinerary {
  const itinerary = itineraryRegistry.get(id)
  if (!itinerary) throw new Error(`Day plan ${id} not found`)
  return itinerary
}

/** Straight lines between waypoints; real trail geometry comes from the api service. */
export async function buildRoute(start: LatLon, end: LatLon, places: Place[], ascentM: number): Promise<Route> {
  const lastPlace = places.at(-1)
  const endIsLastPlace = lastPlace !== undefined && haversineKm(lastPlace, end) < SAME_POINT_KM
  const waypoints: LatLon[] = [start, ...places, ...(endIsLastPlace ? [] : [end])]

  const legKm = waypoints.slice(1).map((point, i) => haversineKm(waypoints[i], point) * TRAIL_WINDING_FACTOR)
  const segmentPhotos = await Promise.all(waypoints.slice(1).map((point, i) => places[i]?.photos ?? photosNearSafe(point)))
  const segments: RouteSegment[] = legKm.map((km, i) => {
    const fromKm = legKm.slice(0, i).reduce((sum, d) => sum + d, 0)
    return { fromKm: round1(fromKm), toKm: round1(fromKm + km), photos: segmentPhotos[i] }
  })

  const distanceKm = round1(legKm.reduce((sum, d) => sum + d, 0))
  const route: Route = {
    id: crypto.randomUUID(),
    geojson: { type: 'LineString', coordinates: waypoints.map((p) => [p.lon, p.lat]) },
    distanceKm,
    ascentM,
    durationMin: Math.round((distanceKm / WALK_KM_PER_HOUR + ascentM / CLIMB_M_PER_HOUR) * 60),
    places,
    segments,
  }
  routeRegistry = new Map([...routeRegistry, [route.id, route]])
  return route
}
