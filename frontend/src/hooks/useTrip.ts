import { useState } from 'react'
import { api } from '../api/client'
import { mergePlaces } from '../lib/places'
import type { ChatMessage, LatLon, Place, PlanMode, Route } from '../types'
import { useAsyncTask } from './useAsyncTask'
import { useDayPlan } from './useDayPlan'
import { usePreferences } from './usePreferences'

export type PickMode = 'start' | 'end' | 'place' | null

const message = (role: ChatMessage['role'], text: string): ChatMessage => ({ id: crypto.randomUUID(), role, text })

export function useTrip() {
  const [sessionId] = useState(() => crypto.randomUUID())
  const [mode, setMode] = useState<PlanMode>('route')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [route, setRoute] = useState<Route | null>(null)
  const [selectedSegment, setSelectedSegment] = useState<number | null>(null)
  const [start, setStart] = useState<LatLon | null>(null)
  const [end, setEnd] = useState<LatLon | null>(null)
  const [places, setPlaces] = useState<Place[]>([])
  const [pickMode, setPickMode] = useState<PickMode>(null)
  const [pendingPoint, setPendingPoint] = useState<LatLon | null>(null)
  const task = useAsyncTask()
  const prefs = usePreferences()
  const day = useDayPlan(task.run)

  const showRoute = (next: Route) => {
    setRoute(next)
    setSelectedSegment(null)
  }

  const sendMessage = (text: string) => {
    setMessages((prev) => [...prev, message('user', text)])
    return task.run(async () => {
      const res = await api.chat({ sessionId, message: text, mode, preferences: prefs.preferences })
      if (res.preferencesPatch) prefs.applyLearned(res.preferencesPatch)
      setMessages((prev) => [...prev, message('assistant', res.reply)])
      setMode(res.mode)
      if (res.mode === 'day' && res.itineraryId) {
        await day.load(res.itineraryId)
        return
      }
      if (res.routeId) {
        showRoute(await api.getRoute(res.routeId))
        return
      }
      // Places without a route (allowed by the contract): show them and drop the route that answered an earlier question.
      setRoute(null)
      setSelectedSegment(null)
      setPlaces((prev) => mergePlaces(prev, res.places))
    })
  }

  const handleMapClick = (point: LatLon) => {
    if (pickMode === 'start') setStart(point)
    if (pickMode === 'end') setEnd(point)
    if (pickMode === 'place') setPendingPoint(point)
    setPickMode(null)
  }

  const savePlace = (name: string, tag: string) => {
    if (!pendingPoint) return Promise.resolve()
    return task.run(async () => {
      const place = await api.addPlace({ name, tags: [tag], ...pendingPoint })
      setPlaces((prev) => [...prev, place])
      setPendingPoint(null)
    })
  }

  const removePlace = (id: string) => setPlaces((prev) => prev.filter((p) => p.id !== id))

  const buildRoute = () => {
    if (!start || !end) return Promise.resolve()
    return task.run(async () => {
      showRoute(await api.createRoute({ start, end, placeIds: places.map((p) => p.id), preferences: [...prefs.preferences.interests] }))
    })
  }

  const buildDayPlan = (startTime: string, endTime: string) => {
    if (!start) return Promise.resolve()
    return day.create({ start, placeIds: places.map((p) => p.id), preferences: prefs.preferences, startTime, endTime })
  }

  return {
    mode, setMode, messages, route, selectedSegment, start, end, places, pickMode, pendingPoint, prefs, day,
    busy: task.busy, error: task.error, clearError: task.clearError,
    sendMessage, handleMapClick, savePlace, removePlace, buildRoute, buildDayPlan,
    setPickMode, setSelectedSegment, cancelPendingPlace: () => setPendingPoint(null),
  }
}

export type Trip = ReturnType<typeof useTrip>
