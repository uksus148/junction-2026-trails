// Shared API contract. Must match "API contract" in /CLAUDE.md — change only together with backend.

export type LatLon = { lat: number; lon: number }

export type Photo = {
  url: string
  thumbUrl: string
  author: string
  license: string
  sourceUrl: string
  lat: number
  lon: number
}

export type Pace = 'relaxed' | 'normal' | 'intense'
/** Max price level the user accepts: 0 free, 1 €, 2 €€, 3 €€€ */
export type Budget = 0 | 1 | 2 | 3
export type CrowdLevel = 0 | 1 | 2

export type Preferences = {
  interests: string[]
  dislikes: string[]
  pace: Pace
  maxWalkKm: number
  budget: Budget
  avoidCrowds: boolean
}

export type PlanMode = 'route' | 'day'

export type OpeningHours = { open: string; close: string } // 'HH:MM'

export type Place = {
  id: string
  name: string
  lat: number
  lon: number
  tags: string[]
  photos: Photo[]
  source: string
  // Optional, used by the day planner. Missing values fall back to defaults.
  dwellMin?: number
  priceLevel?: Budget
  crowdLevel?: CrowdLevel
  openingHours?: OpeningHours
}

export type LineString = {
  type: 'LineString'
  coordinates: [number, number][] // [lon, lat]
}

export type RouteSegment = {
  fromKm: number
  toKm: number
  photos: Photo[]
}

export type Route = {
  id: string
  geojson: LineString
  distanceKm: number
  ascentM: number
  durationMin: number
  places: Place[]
  segments: RouteSegment[]
}

export type ChatRequest = { sessionId: string; message: string; mode: PlanMode; preferences: Preferences }
export type ChatResponse = {
  reply: string
  places: Place[]
  mode: PlanMode
  routeId?: string
  itineraryId?: string
  /** Preferences the agent understood from the message; the client merges them into the profile. */
  preferencesPatch?: Partial<Preferences>
}

export type StopStatus = 'planned' | 'done' | 'skipped'
export type TravelMode = 'walk' | 'transit'

export type ItineraryStop = {
  place: Place
  arriveAt: string // 'HH:MM' — when the visit starts
  leaveAt: string
  travelMin: number
  travelKm: number
  travelMode: TravelMode
  status: StopStatus
}

export type DropReason = 'dislike' | 'budget' | 'closed' | 'no_time' | 'walk_limit' | 'skipped_by_user'
export type DroppedPlace = { place: Place; reason: DropReason }

export type DayPlan = {
  start: LatLon
  startTime: string
  endTime: string
  /** Time from which the not-yet-done part of the day is planned (moves on replan). */
  resumeAt: string
  candidates: Place[] // every place considered for the day
  preferences: Preferences
  stops: ItineraryStop[]
  dropped: DroppedPlace[]
  walkKm: number
}

export type Itinerary = DayPlan & { id: string; route: Route }

export type ItineraryRequest = {
  start: LatLon
  placeIds: string[]
  preferences: Preferences
  startTime: string
  endTime: string
}

export type ReplanRequest = {
  now: string
  location?: LatLon
  skipPlaceIds: string[]
  donePlaceIds: string[]
  preferences?: Preferences
}

export type NewPlace = { name: string; lat: number; lon: number; tags: string[] }

export type RouteRequest = {
  start: LatLon
  end: LatLon
  placeIds: string[]
  preferences: string[]
}

export type ChatMessage = { id: string; role: 'user' | 'assistant'; text: string }

export interface ApiClient {
  chat(request: ChatRequest): Promise<ChatResponse>
  addPlace(place: NewPlace): Promise<Place>
  createRoute(request: RouteRequest): Promise<Route>
  getRoute(id: string): Promise<Route>
  createItinerary(request: ItineraryRequest): Promise<Itinerary>
  getItinerary(id: string): Promise<Itinerary>
  replan(id: string, request: ReplanRequest): Promise<Itinerary>
}
