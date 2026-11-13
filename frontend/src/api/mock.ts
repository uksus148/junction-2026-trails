import { DEMO_ASCENT_M, DEMO_END, DEMO_PLACES, DEMO_START } from '../data/tatras'
import { detectDayPlan, extractPreferencesPatch } from '../lib/intent'
import type { ApiClient, Place } from '../types'
import { createItinerary, dayChat, replanItinerary } from './mockDay'
import { buildRoute, delay, getItinerary, getPlace, getRoute, MOCK_LATENCY_MS, photosNearSafe, registerPlace, withPhotos } from './mockStore'

// In-browser stand-in for api + agent so the frontend works before the backends exist.

// The demo only has a day plan for Bratislava; a Tatras hike request keeps getting the hiking route even in day mode.
const TATRAS_REQUEST = /štrbsk|strbsk|rysy|tatr|skok|штрбске|рысы|татр/iu

export const mockApi: ApiClient = {
  async chat(request) {
    await delay(MOCK_LATENCY_MS)
    const wantsDay = detectDayPlan(request.message) || (request.mode === 'day' && !TATRAS_REQUEST.test(request.message))
    if (wantsDay) return dayChat(request)

    const patch = extractPreferencesPatch(request.message)
    const places = (await Promise.all(DEMO_PLACES.map(withPhotos))).map(registerPlace)
    const route = await buildRoute(DEMO_START, DEMO_END, places, DEMO_ASCENT_M)
    return {
      mode: 'route',
      reply:
        'Here is a route from Štrbské Pleso past Skok waterfall and Popradské pleso up to Rysy. ' +
        'Scroll the strip below to see the views on each part of the trail. (Demo data: the AI agent is not connected yet.)',
      places,
      routeId: route.id,
      ...(Object.keys(patch).length > 0 && { preferencesPatch: patch }),
    }
  },

  async addPlace(newPlace) {
    await delay(MOCK_LATENCY_MS)
    const place: Place = { ...newPlace, id: crypto.randomUUID(), source: 'manual', photos: await photosNearSafe(newPlace) }
    return registerPlace(place)
  },

  async createRoute(request) {
    await delay(MOCK_LATENCY_MS)
    const places = request.placeIds.map(getPlace).filter((place): place is Place => place !== undefined)
    return buildRoute(request.start, request.end, places, 0)
  },

  async getRoute(id) {
    return getRoute(id)
  },

  async createItinerary(request) {
    await delay(MOCK_LATENCY_MS)
    return createItinerary(request)
  },

  async getItinerary(id) {
    return getItinerary(id)
  },

  async replan(id, request) {
    await delay(MOCK_LATENCY_MS)
    return replanItinerary(id, request)
  },
}
