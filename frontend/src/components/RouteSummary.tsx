import { formatAscent, formatDistance, formatDuration } from '../lib/format'
import type { Route } from '../types'

interface RouteSummaryProps {
  route: Route
}

export function RouteSummary({ route }: RouteSummaryProps) {
  const stats = [
    { label: 'Distance', value: formatDistance(route.distanceKm) },
    { label: 'Ascent', value: formatAscent(route.ascentM) },
    { label: 'Walking', value: formatDuration(route.durationMin) },
  ]
  return (
    <dl className="grid grid-cols-3 gap-2 border-t border-line px-5 py-3">
      {stats.map((s) => (
        <div key={s.label}>
          <dt className="text-xs uppercase tracking-wide text-stone">{s.label}</dt>
          <dd className="font-display text-lg font-semibold">{s.value}</dd>
        </div>
      ))}
    </dl>
  )
}
