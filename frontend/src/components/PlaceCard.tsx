import { sourceKind, sourceLink } from '../lib/places'
import type { Place } from '../types'

interface PlaceCardProps {
  place: Place
  onClose: () => void
}

export function PlaceCard({ place, onClose }: PlaceCardProps) {
  const link = sourceLink(place)
  return (
    <section className="absolute top-3 left-3 z-10 w-72 rounded-2xl bg-paper/95 p-4 shadow-xl ring-1 ring-line backdrop-blur" aria-label={`About ${place.name}`}>
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-display text-lg leading-tight font-semibold">{place.name}</h2>
        <button onClick={onClose} className="text-stone hover:text-ink" aria-label="Close place details">
          ×
        </button>
      </div>
      {place.tags.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1">
          {place.tags.map((tag) => (
            <li key={tag} className="rounded-full bg-line px-2 py-0.5 text-xs text-stone">
              {tag}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-sm">
        {link ? (
          <a href={link} target="_blank" rel="noopener noreferrer" className="font-medium text-moss hover:underline">
            Source: {new URL(link).hostname} ↗
          </a>
        ) : (
          // Only "manual" means hand-added; other non-link values (e.g. "fixture") must not claim a provenance.
          <span className="text-stone">{sourceKind(place) === 'manual' ? 'Added manually' : 'Source unavailable'}</span>
        )}
      </p>
    </section>
  )
}
