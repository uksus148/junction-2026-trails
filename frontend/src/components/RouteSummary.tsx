import type { Route } from '../types'

const formatDuration = (min: number) => `${Math.floor(min / 60)}h ${String(min % 60).padStart(2, '0')}m`

interface RouteSummaryProps {
  route: Route
}

export function RouteSummary({ route }: RouteSummaryProps) {
  const stats = [
    { label: 'Distance', value: `${route.distanceKm} km` },
    { label: 'Ascent', value: route.ascentM > 0 ? `${route.ascentM} m` : '—' },
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
