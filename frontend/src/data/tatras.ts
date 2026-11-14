import type { LatLon, NewPlace } from '../types'

// Demo scenario (mock mode only): Štrbské Pleso → Skok waterfall → Popradské pleso, a July hike.
// Rysy was dropped: ORS foot-hiking cannot match it (issue #49, code 2010); see docs/ROUTING_DIAGNOSTICS.md.
// Coordinates follow the OSM objects the live agent selects; real data comes from the backend.

export const DEMO_START: LatLon & { name: string } = { name: 'Štrbské Pleso', lat: 49.1191, lon: 20.0627 }

/** The start as a sourced place: chat returns start, stops and finish as places (docs/AGENT_API_HANDOFF.md, D5). */
export const DEMO_START_PLACE: NewPlace & { id: string; source: string } = {
  id: 'demo-strbske-pleso',
  ...DEMO_START,
  tags: ['lake'],
  source: 'https://en.wikipedia.org/wiki/%C5%A0trbsk%C3%A9_Pleso',
}

const DEMO_FINISH: NewPlace & { id: string; source: string } = {
  id: 'demo-popradske-pleso',
  name: 'Popradské pleso',
  lat: 49.1534,
  lon: 20.0796,
  tags: ['lake'],
  source: 'https://en.wikipedia.org/wiki/Popradsk%C3%A9_pleso',
}

/** Stops in visit order; the last one is the finish (the mock route uses all but the last as stops). */
export const DEMO_PLACES: (NewPlace & { id: string; source: string })[] = [
  {
    id: 'demo-skok',
    name: 'Skok Waterfall',
    lat: 49.1531,
    lon: 20.0453,
    tags: ['waterfall'],
    source: 'https://en.wikipedia.org/wiki/Skok_Waterfall',
  },
  DEMO_FINISH,
]

export const DEMO_END: LatLon = { lat: DEMO_FINISH.lat, lon: DEMO_FINISH.lon }

/** Ascent of the live ORS route for this scenario (docs/ROUTING_DIAGNOSTICS.md: about 741 m). */
export const DEMO_ASCENT_M = 741

/** Revised E5 scenario from #54; keep in sync with the demo request in CLAUDE.md. */
export const DEMO_PROMPT =
  'Plan a summer hike in July from Štrbské Pleso to Popradské pleso via the Skok waterfall. I love wild scenery.'
