/** Route stats arrive from the API as raw floats (e.g. 15.1786 km, 302.015 min); round them for display. */

const MISSING = '—'
const MINUTES_PER_HOUR = 60

export function formatDistance(km: number): string {
  if (!Number.isFinite(km)) return MISSING
  return `${Number(km.toFixed(1))} km`
}

export function formatAscent(metres: number): string {
  const rounded = Math.round(metres)
  return Number.isFinite(rounded) && rounded > 0 ? `${rounded} m` : MISSING
}

export function formatDuration(minutes: number): string {
  if (!Number.isFinite(minutes) || minutes < 0) return MISSING
  // Round first so 59.6 min becomes 1h 00m rather than 0h 60m.
  const total = Math.round(minutes)
  const hours = Math.floor(total / MINUTES_PER_HOUR)
  const rest = total % MINUTES_PER_HOUR
  return `${hours}h ${String(rest).padStart(2, '0')}m`
}
