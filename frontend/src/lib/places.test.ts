import { describe, expect, it } from 'vitest'
import type { Place } from '../types'
import { contextPlaces, mergePlaces, sourceLink } from './places'

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
