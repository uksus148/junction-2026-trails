import { useEffect, useState } from 'react'
import { DEFAULT_PREFERENCES, mergePreferences, parseStoredPreferences } from '../lib/preferences'
import type { Preferences } from '../types'

const STORAGE_KEY = 'gopstop.preferences.v1'

function readStored(): Preferences {
  try {
    return parseStoredPreferences(localStorage.getItem(STORAGE_KEY))
  } catch {
    return DEFAULT_PREFERENCES // storage blocked (private mode, previews)
  }
}

export type PreferenceKey = keyof Preferences

export function usePreferences() {
  const [preferences, setPreferences] = useState<Preferences>(readStored)
  const [learned, setLearned] = useState<PreferenceKey[]>([])

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
    } catch (error) {
      console.warn('Could not save preferences in this browser', error)
    }
  }, [preferences])

  /** Manual edit from the Me tab: the field is no longer "learned". */
  const update = (patch: Partial<Preferences>) => {
    setPreferences((prev) => ({ ...prev, ...patch }))
    setLearned((prev) => prev.filter((key) => !(key in patch)))
  }

  /** Patch understood from the chat: merged and highlighted. */
  const applyLearned = (patch: Partial<Preferences>) => {
    setPreferences((prev) => mergePreferences(prev, patch))
    setLearned((prev) => [...new Set([...prev, ...(Object.keys(patch) as PreferenceKey[])])])
  }

  const reset = () => {
    setPreferences(DEFAULT_PREFERENCES)
    setLearned([])
  }

  return { preferences, learned, update, applyLearned, reset }
}

export type PreferencesState = ReturnType<typeof usePreferences>
