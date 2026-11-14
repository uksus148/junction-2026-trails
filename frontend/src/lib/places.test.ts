import { describe, expect, it } from 'vitest'
import type { Place } from '../types'
import type { Route } from '../types'
import { contextPlaces, mergePlaces, routeEndpoints, sourceKind, sourceLink, uniqueById } from './places'

const place = (id: string, source = 'test'): Place => ({ id, name: id, lat: 49.14, lon: 20.05, tags: ['waterfall'], photos: [], source })

describe('sourceLink', () => {
  it('returns http(s) sources as links', () => {
    expect(sourceLink(place('skok', 'https://en.wikipedia.org/wiki/Skok_Waterfall'))).toBe('https://en.wikipedia.org/wiki/Skok_Waterfall')
  })

  it.each(['manual', 'javascript:alert(1)', ''])('has no link for source "%s"', (source) => {
    expect(sourceLink(place('x', source))).toBeNull()
  })
})

describe('contextPlaces', () => {
  it('returns chat places that the route does not list, in chat order', () => {
    const chat = [place('start'), place('skok'), place('end')]

    expect(contextPlaces([place('skok')], chat).map((p) => p.id)).toEqual(['start', 'end'])
  })

  it('is empty when the route already lists every chat place', () => {
    expect(contextPlaces([place('skok')], [place('skok')])).toEqual([])
  })
})

describe('mergePlaces', () => {
  it('keeps places from a chat reply that has no route', () => {
    expect(mergePlaces([], [place('skok')]).map((p) => p.id)).toEqual(['skok'])
  })

  it('appends new places after the ones already chosen', () => {
    expect(mergePlaces([place('manual')], [place('skok')]).map((p) => p.id)).toEqual(['manual', 'skok'])
  })

  it('does not add a place twice', () => {
    expect(mergePlaces([place('skok')], [place('skok'), place('rysy')]).map((p) => p.id)).toEqual(['skok', 'rysy'])
  })
})

const routeThrough = (stops: Place[]): Route => ({
  id: 'r',
  // The track is snapped by the router, so its ends differ from the stored endpoint places.
  geojson: { type: 'LineString', coordinates: [[20.06, 49.12], [20.05, 49.14], [20.09, 49.18]] },
  distanceKm: 9,
  ascentM: 0,
  durationMin: 120,
  places: stops,
  segments: [],
})

describe('routeEndpoints', () => {
  it('puts A and B on the track ends and takes name and source from the chat endpoints', () => {
    const start = { ...place('start', 'https://example.org/start'), lat: 49.1, lon: 20.0 }
    const end = { ...place('end', 'https://example.org/end'), lat: 49.2, lon: 20.2 }

    const { start: a, end: b } = routeEndpoints(routeThrough([place('skok')]), [start, place('skok'), end])

    expect(a).toEqual({ point: { lat: 49.12, lon: 20.06 }, place: start })
    expect(b).toEqual({ point: { lat: 49.18, lon: 20.09 }, place: end })
  })

  it('keeps both endpoint places for a direct hike with no intermediate stops', () => {
    const { start, end } = routeEndpoints(routeThrough([]), [place('start'), place('end')])

    expect([start?.place?.id, end?.place?.id]).toEqual(['start', 'end'])
  })

  it('has no endpoint places for a route without chat places', () => {
    const { start, end } = routeEndpoints(routeThrough([place('skok')]), [])

    expect([start?.place, end?.place]).toEqual([undefined, undefined])
    expect(end?.point).toEqual({ lat: 49.18, lon: 20.09 })
  })
})

describe('uniqueById', () => {
  it('keeps one entry per place for repeated visits, in first-visit order', () => {
    expect(uniqueById([place('a'), place('b'), place('a')]).map((p) => p.id)).toEqual(['a', 'b'])
  })
})

describe('sourceKind', () => {
  it.each([
    ['https://en.wikipedia.org/wiki/Rysy', 'link'],
    ['manual', 'manual'],
    ['fixture', 'unavailable'],
    ['javascript:alert(1)', 'unavailable'],
  ])('classifies source "%s" as %s', (source, kind) => {
    expect(sourceKind(place('x', source))).toBe(kind)
  })
})
