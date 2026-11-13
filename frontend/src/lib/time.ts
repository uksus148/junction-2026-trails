const MINUTES_PER_DAY = 24 * 60
const TIME_PATTERN = /^(\d{1,2}):(\d{2})$/

/** '09:30' → 570 */
export function toMinutes(hhmm: string): number {
  const match = TIME_PATTERN.exec(hhmm)
  if (!match) throw new Error(`Invalid time "${hhmm}", expected HH:MM`)
  return Number(match[1]) * 60 + Number(match[2])
}

/** 570 → '09:30' (clamped to one day) */
export function fromMinutes(minutes: number): string {
  const clamped = Math.max(0, Math.min(MINUTES_PER_DAY - 1, Math.round(minutes)))
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(Math.floor(clamped / 60))}:${pad(clamped % 60)}`
}

export function addMinutes(hhmm: string, minutes: number): string {
  return fromMinutes(toMinutes(hhmm) + minutes)
}

export function nowHHMM(date: Date = new Date()): string {
  return fromMinutes(date.getHours() * 60 + date.getMinutes())
}
