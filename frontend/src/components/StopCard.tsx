import type { ItineraryStop, Photo } from '../types'

const TRAVEL_LABEL = { walk: 'Walk', transit: 'Transit' } as const
const PHOTOS_PER_STOP = 3

interface StopCardProps {
  stop: ItineraryStop
  index: number
  busy: boolean
  onSkip: (placeId: string) => void
  onDone: (placeId: string) => void
  onOpenPhoto: (photo: Photo) => void
}

export function StopCard({ stop, index, busy, onSkip, onDone, onOpenPhoto }: StopCardProps) {
  const isDone = stop.status === 'done'
  return (
    <li className={`w-64 shrink-0 snap-start rounded-xl border bg-white p-3 transition ${isDone ? 'border-line opacity-60' : 'border-line hover:border-moss'}`}>
      <p className="text-xs text-stone">
        {TRAVEL_LABEL[stop.travelMode]} {stop.travelMin} min · {stop.travelKm} km
      </p>
      <p className="font-display text-lg font-semibold tabular-nums">
        {stop.arriveAt}–{stop.leaveAt}
      </p>
      <p className="mb-2 truncate font-medium" title={stop.place.name}>
        {index + 1}. {stop.place.name}
      </p>
      <div className="mb-2 grid h-14 grid-cols-3 gap-1">
        {stop.place.photos.slice(0, PHOTOS_PER_STOP).map((photo) => (
          <button key={photo.sourceUrl} onClick={() => onOpenPhoto(photo)} className="overflow-hidden rounded-md bg-line" title={`© ${photo.author}`}>
            <img src={photo.thumbUrl} alt="" loading="lazy" className="size-full object-cover" />
          </button>
        ))}
      </div>
      {isDone ? (
        <p className="text-sm font-medium text-moss">✓ Visited</p>
      ) : (
        <div className="flex gap-1.5">
          <button onClick={() => onDone(stop.place.id)} disabled={busy} className="flex-1 rounded-lg bg-moss py-1.5 text-sm font-medium text-white disabled:opacity-40">
            Done
          </button>
          <button onClick={() => onSkip(stop.place.id)} disabled={busy} className="flex-1 rounded-lg py-1.5 text-sm font-medium ring-1 ring-line hover:ring-trail hover:text-trail disabled:opacity-40">
            Skip
          </button>
        </div>
      )}
    </li>
  )
}
