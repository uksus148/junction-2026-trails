import { useCallback, useState } from 'react'
import { getErrorMessage } from '../lib/errors'

export type RunTask = (task: () => Promise<void>) => Promise<void>

/** One shared busy/error state for user-triggered async actions. */
export function useAsyncTask() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run: RunTask = useCallback(async (task) => {
    setBusy(true)
    setError(null)
    try {
      await task()
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }, [])

  return { busy, error, run, clearError: () => setError(null) }
}
