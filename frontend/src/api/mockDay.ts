import { BRATISLAVA_PLACES, BRATISLAVA_START, DEFAULT_DAY_WINDOW } from '../data/bratislava'
import { DROP_REASON_LABELS } from '../lib/dropReasons'
import { extractPreferencesPatch, extractTimeWindow } from '../lib/intent'
import { planDay, replanDay } from '../lib/planner'
import { mergePreferences } from '../lib/preferences'
import type { ChatRequest, ChatResponse, DayPlan, Itinerary, ItineraryRequest, Place, ReplanRequest } from '../types'
import { buildRoute, getItinerary, getPlace, registerPlace, saveItinerary, withPhotos } from './mockStore'

const LEFT_OUT_IN_REPLY = 3

async function toItinerary(plan: DayPlan, id: string = crypto.randomUUID()): Promise<Itinerary> {
  const stopPlaces = plan.stops.map((s) => s.place)
  const route = await buildRoute(plan.start, stopPlaces.at(-1) ?? plan.start, stopPlaces, 0)
  return saveItinerary({ ...plan, id, route })
}

function describeDay(itinerary: Itinerary): string {
  const leftOut = itinerary.dropped
    .slice(0, LEFT_OUT_IN_REPLY)
    .map((d) => `${d.place.name} (${DROP_REASON_LABELS[d.reason]})`)
    .join(', ')
  return [
    `Your day, ${itinerary.startTime}–${itinerary.endTime}: ${itinerary.stops.length} stops, ${itinerary.walkKm} km on foot.`,
    leftOut && `Left out: ${leftOut}.`,
    'Running late or changed your mind? Use Skip, Done or "Running late" and I will rebuild the rest of the day.',
    '(Demo data: the AI agent is not connected yet.)',
  ]
    .filter(Boolean)
    .join(' ')
}

export async function dayChat(request: ChatRequest): Promise<ChatResponse> {
  const patch = extractPreferencesPatch(request.message)
  const preferences = mergePreferences(request.preferences, patch)
  const window = { ...DEFAULT_DAY_WINDOW, ...extractTimeWindow(request.message) }
  const candidates = (await Promise.all(BRATISLAVA_PLACES.map(withPhotos))).map(registerPlace)
  const itinerary = await toItinerary(planDay({ start: BRATISLAVA_START, ...window, candidates, preferences }))
  return {
    mode: 'day',
    reply: describeDay(itinerary),
    places: itinerary.stops.map((s) => s.place),
    itineraryId: itinerary.id,
    ...(Object.keys(patch).length > 0 && { preferencesPatch: patch }),
  }
}

export async function createItinerary(request: ItineraryRequest): Promise<Itinerary> {
  const candidates = request.placeIds.map(getPlace).filter((p): p is Place => p !== undefined)
  return toItinerary(planDay({ ...request, candidates }))
}

export async function replanItinerary(id: string, request: ReplanRequest): Promise<Itinerary> {
  return toItinerary(replanDay(getItinerary(id), request), id)
}
