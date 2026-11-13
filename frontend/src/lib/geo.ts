import type { LatLon } from '../types'

const EARTH_RADIUS_KM = 6371

/** Real paths are longer than straight lines; used to estimate walking distance. */
export const TRAIL_WINDING_FACTOR = 1.35

const toRad = (deg: number) => (deg * Math.PI) / 180

export function haversineKm(a: LatLon, b: LatLon): number {
  const dLat = toRad(b.lat - a.lat)
  const dLon = toRad(b.lon - a.lon)
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(h))
}

const toLatLon = ([lon, lat]: [number, number]): LatLon => ({ lat, lon })

function cumulativeKm(coords: [number, number][]): number[] {
  return coords.reduce<number[]>(
    (acc, point, i) => (i === 0 ? [0] : [...acc, acc[i - 1] + haversineKm(toLatLon(coords[i - 1]), toLatLon(point))]),
    [],
  )
}

function interpolate(a: [number, number], b: [number, number], t: number): [number, number] {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
}

/**
 * Cut the part of a line between two fractions (0..1) of its length.
 * Fractions instead of km so it works even when the reported distance is a trail estimate.
 */
export function sliceLineByFraction(
  coords: [number, number][],
  fromFraction: number,
  toFraction: number,
): [number, number][] {
  if (coords.length < 2) return coords
  const cumulative = cumulativeKm(coords)
  const total = cumulative[cumulative.length - 1]
  if (total === 0) return coords
  const fromKm = total * Math.max(0, fromFraction)
  const toKm = total * Math.min(1, toFraction)

  const pointAt = (km: number): [number, number] => {
    const idx = cumulative.findIndex((d) => d >= km)
    if (idx <= 0) return coords[0]
    const span = cumulative[idx] - cumulative[idx - 1]
    const t = span === 0 ? 0 : (km - cumulative[idx - 1]) / span
    return interpolate(coords[idx - 1], coords[idx], t)
  }

  const inner = coords.filter((_, i) => cumulative[i] > fromKm && cumulative[i] < toKm)
  return [pointAt(fromKm), ...inner, pointAt(toKm)]
}

export function boundsOf(coords: [number, number][]): [[number, number], [number, number]] {
  const lons = coords.map((c) => c[0])
  const lats = coords.map((c) => c[1])
  return [
    [Math.min(...lons), Math.min(...lats)],
    [Math.max(...lons), Math.max(...lats)],
  ]
}
