import { useState } from 'react'
import { api } from '../api/client'
import { haversineKm } from '../lib/geo'
import { addMinutes, nowHHMM } from '../lib/time'
import type { Itinerary, ItineraryRequest, LatLon, Preferences, ReplanRequest } from '../types'
import type { RunTask } from './useAsyncTask'

const GEOLOCATION_TIMEOUT_MS = 5000
const NEARBY_KM = 30 // only trust the device location when the user is actually near the plan

const toLatLon = (p: LatLon): LatLon => ({ lat: p.lat, lon: p.lon })

function currentPosition(): Promise<LatLon | undefined> {
  if (!('geolocation' in navigator)) return Promise.resolve(undefined)
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => resolve(undefined),
      { timeout: GEOLOCATION_TIMEOUT_MS },
    )
  })
}

export function useDayPlan(run: RunTask) {
  const [itinerary, setItinerary] = useState<Itinerary | null>(null)

  /** Raw loader for use inside another running task. */
  const load = async (id: string) => setItinerary(await api.getItinerary(id))

  const replanWith = (build: (current: Itinerary) => Partial<ReplanRequest> | Promise<Partial<ReplanRequest>>) => {
    const current = itinerary
    if (!current) return Promise.resolve()
    return run(async () => {
      const request: ReplanRequest = { now: current.resumeAt, skipPlaceIds: [], donePlaceIds: [], ...(await build(current)) }
      setItinerary(await api.replan(current.id, request))
    })
  }

  const skipStop = (placeId: string) => replanWith(() => ({ skipPlaceIds: [placeId] }))

  /** Marks this stop and every stop before it as visited; the rest is planned from when you leave it. */
  const markDone = (placeId: string) =>
    replanWith((current) => {
      const upTo = current.stops.slice(0, current.stops.findIndex((s) => s.place.id === placeId) + 1)
      const last = upTo.at(-1)
      if (!last) return {}
      return { donePlaceIds: upTo.map((s) => s.place.id), now: last.leaveAt, location: toLatLon(last.place) }
    })

  const runningLate = (minutes: number) => replanWith((current) => ({ now: addMinutes(current.resumeAt, minutes) }))

  const replanNow = () =>
    replanWith(async (current) => {
      const here = await currentPosition()
      const nearby = here && haversineKm(here, current.start) < NEARBY_KM
      return { now: nowHHMM(), ...(nearby && { location: here }) }
    })

  const applyPreferences = (preferences: Preferences) => replanWith(() => ({ preferences }))

  const create = (request: ItineraryRequest) => run(async () => setItinerary(await api.createItinerary(request)))

  return { itinerary, load, create, skipStop, markDone, runningLate, replanNow, applyPreferences }
}

export type DayPlanState = ReturnType<typeof useDayPlan>
