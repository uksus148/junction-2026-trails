import { useState, type FormEvent } from 'react'
import type { PickMode, Trip } from '../hooks/useTrip'
import type { LatLon } from '../types'

const PLACE_TAGS = ['viewpoint', 'waterfall', 'castle', 'peak', 'lake', 'other'] as const

const formatPoint = (p: LatLon) => `${p.lat.toFixed(4)}, ${p.lon.toFixed(4)}`

interface ManualPanelProps {
  trip: Trip
}

export function ManualPanel({ trip }: ManualPanelProps) {
  const { start, end, places, pickMode, pendingPoint, busy } = trip
  const canBuild = start !== null && end !== null

  return (
    <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
      {pickMode && <p className="rounded-xl bg-moss/10 px-3 py-2 text-sm text-moss">Click on the map to place the point.</p>}
      <div className="grid grid-cols-2 gap-2">
        <PickButton label="Start (A)" point={start} mode="start" trip={trip} />
        <PickButton label="Finish (B)" point={end} mode="end" trip={trip} />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-display font-semibold">Places I want to see</h3>
          <button onClick={() => trip.setPickMode('place')} className="text-sm font-medium text-trail hover:underline">
            + Add on map
          </button>
        </div>
        {pendingPoint && <NewPlaceForm point={pendingPoint} busy={busy} onSave={trip.savePlace} onCancel={trip.cancelPendingPlace} />}
        <ol className="space-y-1.5">
          {places.map((p, i) => (
            <li key={p.id} className="flex items-center gap-3 rounded-xl bg-white px-3 py-2 ring-1 ring-line">
              <span className="grid size-6 place-items-center rounded-full bg-trail text-xs font-semibold text-white">{i + 1}</span>
              <span className="flex-1 truncate">{p.name}</span>
              <span className="text-xs text-stone">{p.tags.join(', ')}</span>
              <button onClick={() => trip.removePlace(p.id)} className="text-stone hover:text-ink" aria-label={`Remove ${p.name}`}>
                ×
              </button>
            </li>
          ))}
          {places.length === 0 && !pendingPoint && <li className="text-sm text-stone">No places yet.</li>}
        </ol>
      </div>

      <button
        onClick={() => void trip.buildRoute()}
        disabled={!canBuild || busy}
        className="w-full rounded-xl bg-trail py-3 font-medium text-white transition hover:brightness-110 disabled:opacity-40"
      >
        {busy ? 'Building route…' : 'Build route'}
      </button>
    </div>
  )
}

interface PickButtonProps {
  label: string
  point: LatLon | null
  mode: PickMode
  trip: Trip
}

function PickButton({ label, point, mode, trip }: PickButtonProps) {
  const active = trip.pickMode === mode
  return (
    <button
      onClick={() => trip.setPickMode(active ? null : mode)}
      className={`rounded-xl px-3 py-2 text-left ring-1 transition ${active ? 'bg-moss text-white ring-moss' : 'bg-white ring-line hover:ring-moss'}`}
    >
      <span className="block text-sm font-medium">{label}</span>
      <span className={`block text-xs ${active ? 'text-white/80' : 'text-stone'}`}>{point ? formatPoint(point) : 'Click to set'}</span>
    </button>
  )
}

interface NewPlaceFormProps {
  point: LatLon
  busy: boolean
  onSave: (name: string, tag: string) => Promise<void>
  onCancel: () => void
}

function NewPlaceForm({ point, busy, onSave, onCancel }: NewPlaceFormProps) {
  const [name, setName] = useState('')
  const [tag, setTag] = useState<string>(PLACE_TAGS[0])

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (name.trim()) void onSave(name.trim(), tag)
  }

  return (
    <form onSubmit={submit} className="mb-3 space-y-2 rounded-xl bg-white p-3 ring-1 ring-trail">
      <p className="text-xs text-stone">{formatPoint(point)}</p>
      <input
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Name, e.g. Skok waterfall"
        className="w-full rounded-lg border border-line px-3 py-2 outline-none focus:border-moss"
      />
      <select value={tag} onChange={(e) => setTag(e.target.value)} className="w-full rounded-lg border border-line bg-white px-3 py-2">
        {PLACE_TAGS.map((t) => (
          <option key={t}>{t}</option>
        ))}
      </select>
      <div className="flex gap-2">
        <button type="submit" disabled={busy || !name.trim()} className="flex-1 rounded-lg bg-ink py-2 text-sm font-medium text-white disabled:opacity-40">
          Save place
        </button>
        <button type="button" onClick={onCancel} className="rounded-lg px-3 text-sm text-stone hover:text-ink">
          Cancel
        </button>
      </div>
    </form>
  )
}
