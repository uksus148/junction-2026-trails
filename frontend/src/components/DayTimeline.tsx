import { DROP_REASON_LABELS } from '../lib/dropReasons'
import type { Itinerary, Photo } from '../types'
import { StopCard } from './StopCard'

const LATE_OPTIONS_MIN = [15, 30, 60]

interface DayTimelineProps {
  itinerary: Itinerary
  busy: boolean
  onSkip: (placeId: string) => void
  onDone: (placeId: string) => void
  onLate: (minutes: number) => void
  onReplanNow: () => void
  onOpenPhoto: (photo: Photo) => void
}

export function DayTimeline({ itinerary, busy, onSkip, onDone, onLate, onReplanNow, onOpenPhoto }: DayTimelineProps) {
  const replanned = itinerary.resumeAt !== itinerary.startTime
  return (
    <section className="pointer-events-none absolute inset-x-0 bottom-0 p-3 md:p-4" aria-label="Your day plan">
      <div className="pointer-events-auto rounded-2xl bg-paper/95 p-3 shadow-xl ring-1 ring-line backdrop-blur">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2 px-1">
          <div>
            <h2 className="font-display font-semibold">
              Your day · {itinerary.startTime}–{itinerary.endTime}
            </h2>
            <p className="text-sm text-stone">
              {itinerary.stops.length} stops · {itinerary.walkKm} km on foot
              {replanned && ` · replanned from ${itinerary.resumeAt}`}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-stone">Running late</span>
            {LATE_OPTIONS_MIN.map((m) => (
              <button key={m} onClick={() => onLate(m)} disabled={busy} className="rounded-lg bg-white px-2.5 py-1 text-sm font-medium ring-1 ring-line hover:ring-trail disabled:opacity-40">
                +{m}m
              </button>
            ))}
            <button onClick={onReplanNow} disabled={busy} className="rounded-lg bg-ink px-3 py-1 text-sm font-medium text-white disabled:opacity-40">
              Replan from now
            </button>
          </div>
        </div>

        {itinerary.stops.length === 0 ? (
          <p className="rounded-xl bg-white px-3 py-4 text-sm text-stone">Nothing fits any more. Try a later end time or loosen your preferences in the Me tab.</p>
        ) : (
          <ol className="flex snap-x gap-3 overflow-x-auto pb-1">
            {itinerary.stops.map((stop, i) => (
              <StopCard key={stop.place.id} stop={stop} index={i} busy={busy} onSkip={onSkip} onDone={onDone} onOpenPhoto={onOpenPhoto} />
            ))}
          </ol>
        )}

        {itinerary.dropped.length > 0 && (
          <details className="mt-2 px-1 text-sm">
            <summary className="cursor-pointer text-stone hover:text-ink">Left out ({itinerary.dropped.length}) and why</summary>
            <ul className="mt-1 grid gap-x-6 gap-y-0.5 sm:grid-cols-2">
              {itinerary.dropped.map((d) => (
                <li key={d.place.id}>
                  <span className="font-medium">{d.place.name}</span> <span className="text-stone">— {DROP_REASON_LABELS[d.reason]}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </section>
  )
}
