import type { ReactNode } from 'react'
import type { PreferenceKey, PreferencesState } from '../hooks/usePreferences'
import { PLACE_TAGS } from '../lib/preferences'
import type { Budget, Pace } from '../types'

const TAG_LABELS: Record<(typeof PLACE_TAGS)[number], string> = {
  castle: 'Castles',
  museum: 'Museums',
  church: 'Churches',
  viewpoint: 'Views',
  nature: 'Nature',
  waterfall: 'Waterfalls',
  lake: 'Lakes',
  peak: 'Peaks',
  oldtown: 'Old towns',
}

const PACE_OPTIONS: { value: Pace; label: string }[] = [
  { value: 'relaxed', label: 'Relaxed' },
  { value: 'normal', label: 'Normal' },
  { value: 'intense', label: 'Intense' },
]

const BUDGET_OPTIONS: { value: Budget; label: string }[] = [
  { value: 0, label: 'Free' },
  { value: 1, label: '€' },
  { value: 2, label: '€€' },
  { value: 3, label: '€€€' },
]

const WALK_MIN_KM = 1
const WALK_MAX_KM = 25

interface PreferencesPanelProps {
  prefs: PreferencesState
  canUpdateDay: boolean
  busy: boolean
  onUpdateDay: () => void
}

export function PreferencesPanel({ prefs, canUpdateDay, busy, onUpdateDay }: PreferencesPanelProps) {
  const { preferences: p, update, learned } = prefs
  const isLearned = (key: PreferenceKey) => learned.includes(key)

  const toggle = (list: 'interests' | 'dislikes', tag: string) => {
    const other = list === 'interests' ? 'dislikes' : 'interests'
    const has = p[list].includes(tag)
    update({ [list]: has ? p[list].filter((t) => t !== tag) : [...p[list], tag], [other]: p[other].filter((t) => t !== tag) })
  }

  return (
    <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-4">
      <Section title="I love" learned={isLearned('interests')}>
        <Chips selected={p.interests} tone="like" onToggle={(tag) => toggle('interests', tag)} />
      </Section>
      <Section title="Not for me" learned={isLearned('dislikes')}>
        <Chips selected={p.dislikes} tone="dislike" onToggle={(tag) => toggle('dislikes', tag)} />
      </Section>
      <Section title="Pace" learned={isLearned('pace')}>
        <Segmented options={PACE_OPTIONS} value={p.pace} onChange={(pace) => update({ pace })} />
      </Section>
      <Section title={`Walking per day: up to ${p.maxWalkKm} km`} learned={isLearned('maxWalkKm')}>
        <input
          type="range"
          min={WALK_MIN_KM}
          max={WALK_MAX_KM}
          value={p.maxWalkKm}
          onChange={(e) => update({ maxWalkKm: Number(e.target.value) })}
          className="w-full accent-moss"
          aria-label="Maximum walking distance per day in kilometres"
        />
      </Section>
      <Section title="Budget per place" learned={isLearned('budget')}>
        <Segmented options={BUDGET_OPTIONS} value={p.budget} onChange={(budget) => update({ budget })} />
      </Section>
      <Section title="Crowds" learned={isLearned('avoidCrowds')}>
        <label className="flex cursor-pointer items-center justify-between rounded-xl bg-white px-3 py-2 ring-1 ring-line">
          <span className="text-sm">Avoid busy places</span>
          <input type="checkbox" checked={p.avoidCrowds} onChange={(e) => update({ avoidCrowds: e.target.checked })} className="size-4 accent-moss" />
        </label>
      </Section>

      <div className="flex gap-2">
        {canUpdateDay && (
          <button onClick={onUpdateDay} disabled={busy} className="flex-1 rounded-xl bg-trail py-2.5 font-medium text-white transition hover:brightness-110 disabled:opacity-40">
            Update my day
          </button>
        )}
        <button onClick={prefs.reset} className="rounded-xl px-3 py-2.5 text-sm text-stone hover:text-ink">
          Reset
        </button>
      </div>
    </div>
  )
}

function Section({ title, learned, children }: { title: string; learned: boolean; children: ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 flex items-center gap-2 font-display text-sm font-semibold">
        {title}
        {learned && <span className="rounded-full bg-moss/10 px-2 py-0.5 text-[11px] font-medium text-moss">from chat</span>}
      </h3>
      {children}
    </section>
  )
}

function Chips({ selected, tone, onToggle }: { selected: string[]; tone: 'like' | 'dislike'; onToggle: (tag: string) => void }) {
  const activeClass = tone === 'like' ? 'bg-moss text-white ring-moss' : 'bg-ink text-white ring-ink line-through decoration-white/50'
  return (
    <div className="flex flex-wrap gap-1.5">
      {PLACE_TAGS.map((tag) => {
        const active = selected.includes(tag)
        return (
          <button
            key={tag}
            aria-pressed={active}
            onClick={() => onToggle(tag)}
            className={`rounded-full px-3 py-1 text-sm ring-1 transition ${active ? activeClass : 'bg-white ring-line hover:ring-moss'}`}
          >
            {TAG_LABELS[tag]}
          </button>
        )
      })}
    </div>
  )
}

interface SegmentedProps<T extends string | number> {
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
}

function Segmented<T extends string | number>({ options, value, onChange }: SegmentedProps<T>) {
  return (
    <div className="flex gap-1 rounded-xl bg-line/60 p-1" role="radiogroup">
      {options.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={o.value === value}
          onClick={() => onChange(o.value)}
          className={`flex-1 rounded-lg py-1.5 text-sm font-medium transition ${o.value === value ? 'bg-white shadow-sm' : 'text-stone hover:text-ink'}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
