import { describe, expect, it } from 'vitest'
import type { Photo, Route, RouteSegment } from '../types'
import { routeHasPhotos } from './routes'

const photo: Photo = { url: 'u', thumbUrl: 't', author: 'a', license: 'CC BY-SA 4.0', sourceUrl: 'https://example.org', lat: 49, lon: 20 }

const route = (segments: RouteSegment[]): Route => ({
  id: 'r',
  geojson: { type: 'LineString', coordinates: [[20, 49], [20.1, 49.1]] },
  distanceKm: 5,
  ascentM: 0,
  durationMin: 60,
  places: [],
  segments,
})

describe('routeHasPhotos', () => {
  it('is false for a route without segments, which the API may return before photos exist', () => {
    expect(routeHasPhotos(route([]))).toBe(false)
  })

  it('is false when every segment has an empty photo list', () => {
    expect(routeHasPhotos(route([{ fromKm: 0, toKm: 2, photos: [] }, { fromKm: 2, toKm: 5, photos: [] }]))).toBe(false)
  })

  it('is true when at least one segment has a photo', () => {
    expect(routeHasPhotos(route([{ fromKm: 0, toKm: 2, photos: [] }, { fromKm: 2, toKm: 5, photos: [photo] }]))).toBe(true)
  })
})
