import { DEMO_ASCENT_M, DEMO_END, DEMO_PLACES, DEMO_START } from '../data/tatras'
import type { ApiClient, Place } from '../types'
import { buildRoute, delay, getPlace, getRoute, MOCK_LATENCY_MS, photosNearSafe, registerPlace, withPhotos } from './mockStore'

// In-browser stand-in for api + agent so the frontend works before the backends exist.

export const mockApi: ApiClient = {
  async chat() {
    await delay(MOCK_LATENCY_MS)
    const places = (await Promise.all(DEMO_PLACES.map(withPhotos))).map(registerPlace)
    const route = await buildRoute(DEMO_START, DEMO_END, places, DEMO_ASCENT_M)
    return {
      reply:
        'Here is a route from Štrbské Pleso past Skok waterfall and Popradské pleso up to Rysy. ' +
        'Scroll the strip below to see the views on each part of the trail. (Demo data: the AI agent is not connected yet.)',
      places,
      routeId: route.id,
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
}
