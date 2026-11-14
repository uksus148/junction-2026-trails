import type { LatLon, NewPlace } from '../types'

// Demo scenario (mock mode only): Štrbské Pleso → Skok waterfall → Popradské pleso → Rysy.
// Coordinates are approximate; real data comes from the backend.

export const DEMO_START: LatLon & { name: string } = { name: 'Štrbské Pleso', lat: 49.1191, lon: 20.0627 }

export const DEMO_PLACES: (NewPlace & { id: string; source: string })[] = [
  {
    id: 'demo-skok',
    name: 'Skok Waterfall',
    lat: 49.1425,
    lon: 20.0506,
    tags: ['waterfall'],
    source: 'https://en.wikipedia.org/wiki/Skok_Waterfall',
  },
  {
    id: 'demo-popradske-pleso',
    name: 'Popradské pleso',
    lat: 49.1534,
    lon: 20.0796,
    tags: ['lake', 'viewpoint'],
    source: 'https://en.wikipedia.org/wiki/Popradsk%C3%A9_pleso',
  },
  {
    id: 'demo-rysy',
    name: 'Rysy',
    lat: 49.1795,
    lon: 20.088,
    tags: ['peak', 'viewpoint'],
    source: 'https://en.wikipedia.org/wiki/Rysy',
  },
]

export const DEMO_END: LatLon = { lat: 49.1795, lon: 20.088 }

export const DEMO_ASCENT_M = 1250

export const DEMO_PROMPT =
  'I want to hike from Štrbské Pleso up to Rysy and see the Skok waterfall on the way. I love wild views.'
