import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { ChatMessage } from '../types'

interface ChatPanelProps {
  messages: ChatMessage[]
  busy: boolean
  suggestions: string[]
  onSend: (text: string) => void
}

export function ChatPanel({ messages, busy, suggestions, onSend }: ChatPanelProps) {
  const [draft, setDraft] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    const text = draft.trim()
    if (!text || busy) return
    onSend(text)
    setDraft('')
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {messages.length === 0 && <EmptyState suggestions={suggestions} onPick={onSend} disabled={busy} />}
        {messages.map((m) => (
          <p
            key={m.id}
            className={`max-w-[90%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed ${m.role === 'user' ? 'ml-auto bg-ink text-white' : 'bg-white ring-1 ring-line'}`}
          >
            {m.text}
          </p>
        ))}
        {busy && <p className="animate-pulse text-sm text-stone">Searching the web for places and views…</p>}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit} className="border-t border-line p-3">
        <div className="flex items-end gap-2 rounded-2xl bg-white p-2 ring-1 ring-line focus-within:ring-moss">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) submit(e)
            }}
            rows={2}
            placeholder="Where do you want to go, and what do you want to see?"
            className="min-h-0 flex-1 resize-none bg-transparent px-2 py-1 text-[15px] outline-none placeholder:text-stone"
          />
          <button type="submit" disabled={busy || !draft.trim()} className="rounded-xl bg-trail px-4 py-2 font-medium text-white transition hover:brightness-110 disabled:opacity-40">
            Go
          </button>
        </div>
      </form>
    </div>
  )
}

interface EmptyStateProps {
  suggestions: string[]
  onPick: (text: string) => void
  disabled: boolean
}

function EmptyState({ suggestions, onPick, disabled }: EmptyStateProps) {
  return (
    <div className="space-y-3 pt-2">
      <p className="text-[15px] text-stone">
        Describe the trip in your own words: where you start, what you want to see, and what you'd rather skip. Ask for a day plan and you
        get a timed schedule that rebuilds itself when plans change.
      </p>
      <div className="space-y-2">
        {suggestions.map((s) => (
          <button
            key={s}
            disabled={disabled}
            onClick={() => onPick(s)}
            className="block w-full rounded-xl border border-dashed border-line px-3 py-2 text-left text-sm transition hover:border-moss hover:bg-white"
          >
            “{s}”
          </button>
        ))}
      </div>
    </div>
  )
}
