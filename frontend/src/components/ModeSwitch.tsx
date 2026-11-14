import type { PlanMode } from '../types'

interface ModeSwitchProps {
  mode: PlanMode
  onChange: (mode: PlanMode) => void
}

export function ModeSwitch({ mode, onChange }: ModeSwitchProps) {
  const isDay = mode === 'day'
  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDay}
      onClick={() => onChange(isDay ? 'route' : 'day')}
      className={`flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-left ring-1 transition ${isDay ? 'bg-moss/10 ring-moss' : 'bg-white ring-line hover:ring-moss'}`}
    >
      <span>
        <span className="block text-sm font-medium">Day plan</span>
        <span className="block text-xs text-stone">
          {isDay ? 'A timed schedule that adapts when your day changes' : 'Off: one route from A to B'}
        </span>
      </span>
      <span className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${isDay ? 'bg-moss' : 'bg-line'}`} aria-hidden="true">
        <span className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-transform ${isDay ? 'translate-x-5.5' : 'translate-x-0.5'}`} />
      </span>
    </button>
  )
}
