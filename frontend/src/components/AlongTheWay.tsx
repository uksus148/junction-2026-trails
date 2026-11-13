import type { Photo, Route } from '../types'

interface AlongTheWayProps {
  route: Route
  selectedSegment: number | null
  onSelectSegment: (index: number | null) => void
  onOpenPhoto: (photo: Photo) => void
}

const PHOTOS_PER_SEGMENT = 4

export function AlongTheWay({ route, selectedSegment, onSelectSegment, onOpenPhoto }: AlongTheWayProps) {
  return (
    <section className="pointer-events-none absolute inset-x-0 bottom-0 p-3 md:p-4" aria-label="What you will see along the way">
      <div className="pointer-events-auto rounded-2xl bg-paper/95 p-3 shadow-xl ring-1 ring-line backdrop-blur">
        <h2 className="mb-2 px-1 font-display text-sm font-semibold uppercase tracking-wide text-stone">What you'll see on the way</h2>
        <ol className="flex snap-x gap-3 overflow-x-auto pb-1">
          {route.segments.map((segment, i) => {
            const active = selectedSegment === i
            const destination = route.places[i]?.name ?? 'Finish'
            return (
              <li key={`${segment.fromKm}-${i}`} className="snap-start">
                <div className={`w-72 shrink-0 rounded-xl border p-2 transition ${active ? 'border-moss bg-white shadow' : 'border-line bg-white/60 hover:bg-white'}`}>
                  <button className="mb-2 flex w-full items-baseline justify-between gap-2 text-left" onClick={() => onSelectSegment(active ? null : i)}>
                    <span className="truncate font-medium">
                      {i + 1}. to {destination}
                    </span>
                    <span className="shrink-0 text-xs text-stone">
                      {segment.fromKm}–{segment.toKm} km
                    </span>
                  </button>
                  <SegmentPhotos photos={segment.photos} onOpenPhoto={onOpenPhoto} />
                </div>
              </li>
            )
          })}
        </ol>
      </div>
    </section>
  )
}

interface SegmentPhotosProps {
  photos: Photo[]
  onOpenPhoto: (photo: Photo) => void
}

function SegmentPhotos({ photos, onOpenPhoto }: SegmentPhotosProps) {
  if (photos.length === 0) {
    return <p className="grid h-20 place-items-center rounded-lg bg-line/50 text-xs text-stone">No photos for this part yet</p>
  }
  return (
    <div className="grid grid-cols-4 gap-1">
      {photos.slice(0, PHOTOS_PER_SEGMENT).map((photo) => (
        <button key={photo.sourceUrl} onClick={() => onOpenPhoto(photo)} className="aspect-square overflow-hidden rounded-md bg-line" title={`© ${photo.author}`}>
          <img src={photo.thumbUrl} alt="" loading="lazy" className="size-full object-cover transition hover:scale-105" />
        </button>
      ))}
    </div>
  )
}
