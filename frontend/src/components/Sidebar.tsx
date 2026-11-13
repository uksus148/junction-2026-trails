import { useState } from 'react'
import { USE_MOCKS } from '../api/client'
import { DAY_DEMO_PROMPT, DAY_DEMO_PROMPT_ALT } from '../data/bratislava'
import { DEMO_PROMPT } from '../data/tatras'
import type { Trip } from '../hooks/useTrip'
import { ChatPanel } from './ChatPanel'
import { ManualPanel } from './ManualPanel'
import { ModeSwitch } from './ModeSwitch'
import { PreferencesPanel } from './PreferencesPanel'
import { RouteSummary } from './RouteSummary'

type Tab = 'chat' | 'manual' | 'me'

const TABS: { id: Tab; label: string }[] = [
  { id: 'chat', label: 'Ask' },
  { id: 'manual', label: 'Plan on map' },
  { id: 'me', label: 'Me' },
]

const SUGGESTIONS = {
  route: [DEMO_PROMPT, DAY_DEMO_PROMPT],
  day: [DAY_DEMO_PROMPT, DAY_DEMO_PROMPT_ALT],
}

interface SidebarProps {
  trip: Trip
}

export function Sidebar({ trip }: SidebarProps) {
  const [tab, setTab] = useState<Tab>('chat')
  const isDay = trip.mode === 'day'
  return (
    <aside className="flex h-[55dvh] min-h-0 flex-col border-line bg-paper md:h-auto md:w-[420px] md:border-r">
      <header className="space-y-3 px-5 pt-5 pb-3">
        <div>
          <div className="flex items-center justify-between">
            <h1 className="font-display text-xl font-bold tracking-tight">GOPSTOP.PROTOCOL</h1>
            {USE_MOCKS && <span className="rounded-full bg-line px-2 py-0.5 text-xs text-stone">demo data</span>}
          </div>
          <p className="mt-1 text-sm text-stone">Routes built around what you want to see.</p>
        </div>
        <ModeSwitch mode={trip.mode} onChange={trip.setMode} />
        <nav className="flex gap-1 rounded-xl bg-line/60 p-1" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 rounded-lg py-1.5 text-sm font-medium transition ${tab === t.id ? 'bg-white shadow-sm' : 'text-stone hover:text-ink'}`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {trip.error && (
        <div className="mx-5 mb-2 flex items-start justify-between gap-3 rounded-xl bg-trail/10 px-3 py-2 text-sm text-trail" role="alert">
          <span>{trip.error}</span>
          <button onClick={trip.clearError} aria-label="Dismiss error">
            ×
          </button>
        </div>
      )}

      {tab === 'chat' && (
        <ChatPanel messages={trip.messages} busy={trip.busy} suggestions={SUGGESTIONS[trip.mode]} onSend={(text) => void trip.sendMessage(text)} />
      )}
      {tab === 'manual' && <ManualPanel trip={trip} />}
      {tab === 'me' && (
        <PreferencesPanel
          prefs={trip.prefs}
          busy={trip.busy}
          canUpdateDay={isDay && trip.day.itinerary !== null}
          onUpdateDay={() => void trip.day.applyPreferences(trip.prefs.preferences)}
        />
      )}

      {!isDay && trip.route && <RouteSummary route={trip.route} />}
    </aside>
  )
}
