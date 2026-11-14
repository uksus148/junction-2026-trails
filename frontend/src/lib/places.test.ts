import { describe, expect, it } from 'vitest'
import type { Place } from '../types'
import { mergePlaces } from './places'

const place = (id: string): Place => ({ id, name: id, lat: 49.14, lon: 20.05, tags: ['waterfall'], photos: [], source: 'test' })

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
