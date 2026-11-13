import type { LatLon, Place } from '../types'

// Day-plan demo (mock mode only). Coordinates, hours and prices are approximate.

export const BRATISLAVA_START: LatLon & { name: string } = { name: 'Hodžovo námestie', lat: 48.1477, lon: 17.1074 }

export const DEFAULT_DAY_WINDOW = { startTime: '10:00', endTime: '18:00' }

const wiki = (title: string) => `https://en.wikipedia.org/wiki/${title}`

export const BRATISLAVA_PLACES: Omit<Place, 'photos'>[] = [
  { id: 'ba-castle', name: 'Bratislava Castle', lat: 48.1422, lon: 17.1, tags: ['castle', 'viewpoint'], source: wiki('Bratislava_Castle'), dwellMin: 60, priceLevel: 1, crowdLevel: 2, openingHours: { open: '09:00', close: '21:00' } },
  { id: 'ba-cathedral', name: "St. Martin's Cathedral", lat: 48.1417, lon: 17.1046, tags: ['church'], source: wiki("St._Martin's_Cathedral,_Bratislava"), dwellMin: 30, priceLevel: 1, crowdLevel: 1, openingHours: { open: '09:00', close: '18:00' } },
  { id: 'ba-main-square', name: 'Main Square & Old Town Hall', lat: 48.1437, lon: 17.1076, tags: ['oldtown'], source: wiki('Old_Town_Hall_(Bratislava)'), dwellMin: 30, priceLevel: 0, crowdLevel: 2 },
  { id: 'ba-michaels-gate', name: "Michael's Gate", lat: 48.1452, lon: 17.1066, tags: ['oldtown', 'viewpoint'], source: wiki("Michael's_Gate"), dwellMin: 25, priceLevel: 1, crowdLevel: 2, openingHours: { open: '10:00', close: '18:00' } },
  { id: 'ba-primates-palace', name: "Primate's Palace", lat: 48.144, lon: 17.1093, tags: ['museum'], source: wiki("Primate's_Palace"), dwellMin: 45, priceLevel: 1, crowdLevel: 0, openingHours: { open: '10:00', close: '17:00' } },
  { id: 'ba-blue-church', name: 'Blue Church', lat: 48.1436, lon: 17.1163, tags: ['church'], source: wiki('Church_of_St._Elisabeth'), dwellMin: 20, priceLevel: 0, crowdLevel: 1, openingHours: { open: '07:00', close: '19:00' } },
  { id: 'ba-gallery', name: 'Slovak National Gallery', lat: 48.1404, lon: 17.1108, tags: ['museum'], source: wiki('Slovak_National_Gallery'), dwellMin: 75, priceLevel: 1, crowdLevel: 0, openingHours: { open: '10:00', close: '18:00' } },
  { id: 'ba-ufo', name: 'UFO Observation Deck', lat: 48.1376, lon: 17.105, tags: ['viewpoint'], source: wiki('Most_SNP'), dwellMin: 45, priceLevel: 3, crowdLevel: 2, openingHours: { open: '10:00', close: '23:00' } },
  { id: 'ba-danube', name: 'Danube Promenade', lat: 48.1403, lon: 17.122, tags: ['nature'], source: wiki('Eurovea'), dwellMin: 40, priceLevel: 0, crowdLevel: 1 },
  { id: 'ba-devin', name: 'Devín Castle', lat: 48.1737, lon: 16.9785, tags: ['castle', 'viewpoint', 'nature'], source: wiki('Devín_Castle'), dwellMin: 90, priceLevel: 1, crowdLevel: 1, openingHours: { open: '10:00', close: '17:00' } },
  { id: 'ba-kamzik', name: 'Kamzík TV Tower', lat: 48.1828, lon: 17.0951, tags: ['viewpoint', 'nature'], source: wiki('Kamzík_TV_Tower'), dwellMin: 60, priceLevel: 2, crowdLevel: 0, openingHours: { open: '10:00', close: '22:00' } },
]

export const DAY_DEMO_PROMPT = 'Plan my day in Bratislava from 10:00, no museums please, I hate crowds'
export const DAY_DEMO_PROMPT_ALT = 'Plan my day in Bratislava from 9:00 until 17:00, I love castles and views, slow pace'
