import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, MapMouseEvent } from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef, useState } from 'react'
import { boundsOf, sliceLineByFraction } from '../lib/geo'
import { contextPlaces } from '../lib/places'
import type { LatLon, Place, Route } from '../types'
import type { PickMode } from '../hooks/useTrip'

// Bundlers move MapLibre's module, so its self-relative worker lookup fails — point it at the worker explicitly.
maplibregl.setWorkerUrl(maplibreWorkerUrl)

const MAP_STYLE ='https://tiles.openfreemap.org/styles/liberty'
const DEFAULT_CENTER: [number, number] = [20.07, 49.15]
const DEFAULT_ZOOM = 11
const FIT_PADDING = { top: 60, bottom: 280, left: 60, right: 60 }
const EMPTY_LINE = { type: 'Feature' as const, properties: {}, geometry: { type: 'LineString' as const, coordinates: [] } }

interface MapViewProps {
  route: Route | null
  selectedSegment: number | null
  start: LatLon | null
  end: LatLon | null
  places: Place[]
  chatPlaces: Place[]
  pendingPoint: LatLon | null
  pickMode: PickMode
  onMapClick: (point: LatLon) => void
  onSelectPlace: (placeId: string) => void
}

type MarkerSpec = { point: LatLon; label: string; title: string; variant: 'start' | 'end' | 'place' | 'pending'; placeId?: string }

const MARKER_CLASSES: Record<MarkerSpec['variant'], string> = {
  start: 'bg-moss text-white',
  end: 'bg-ink text-white',
  place: 'bg-trail text-white',
  pending: 'bg-white text-trail border-2 border-dashed border-trail',
}

function markerElement(spec: MarkerSpec, onSelect: (placeId: string) => void): HTMLElement {
  const el = document.createElement('div')
  // No transition/transform utilities here: MapLibre positions markers with `transform`, and animating it
  // makes the marker slide away between mousedown and mouseup, so the click never lands.
  const clickable = spec.placeId ? 'cursor-pointer hover:brightness-110' : ''
  el.className = `grid size-8 place-items-center rounded-full text-sm font-semibold shadow-lg ring-2 ring-white ${MARKER_CLASSES[spec.variant]} ${clickable}`
  el.textContent = spec.label
  el.title = spec.title
  const { placeId } = spec
  if (placeId) {
    el.setAttribute('role', 'button')
    el.addEventListener('click', (event) => {
      event.stopPropagation() // don't also count as a map click while picking points
      onSelect(placeId)
    })
  }
  return el
}

const toLatLon = (coordinate: [number, number] | undefined): LatLon | null =>
  coordinate ? { lat: coordinate[1], lon: coordinate[0] } : null

/** Start and finish come from the chat's places when it returned them, otherwise from the track's ends. */
function endpointSpecs(props: MapViewProps): MarkerSpec[] {
  const coordinates = props.route?.geojson.coordinates ?? []
  const extra = contextPlaces(props.route?.places ?? [], props.chatPlaces)
  const startPlace = extra.find((p) => p.id === props.chatPlaces[0]?.id)
  const endPlace = extra.find((p) => p.id === props.chatPlaces.at(-1)?.id && p.id !== startPlace?.id)
  const start = props.start ?? startPlace ?? toLatLon(coordinates[0])
  const end = props.end ?? endPlace ?? (props.route ? toLatLon(coordinates.at(-1)) : null)
  return [
    ...(start ? [{ point: start, label: 'A', title: startPlace?.name ?? 'Start', variant: 'start' as const, placeId: startPlace?.id }] : []),
    ...(end ? [{ point: end, label: 'B', title: endPlace?.name ?? 'Finish', variant: 'end' as const, placeId: endPlace?.id }] : []),
  ]
}

function markerSpecs(props: MapViewProps): MarkerSpec[] {
  const routePlaces = props.route?.places ?? props.places
  return [
    ...endpointSpecs(props),
    ...routePlaces.map((p, i) => ({ point: p, label: String(i + 1), title: p.name, variant: 'place' as const, placeId: p.id })),
    ...(props.pendingPoint ? [{ point: props.pendingPoint, label: '+', title: 'New place', variant: 'pending' as const }] : []),
  ]
}

const LINE_LAYOUT = { 'line-join': 'round', 'line-cap': 'round' } as const

function addRouteLayers(map: maplibregl.Map) {
  map.addSource('route', { type: 'geojson', data: EMPTY_LINE })
  map.addSource('segment', { type: 'geojson', data: EMPTY_LINE })
  map.addLayer({ id: 'route-casing', type: 'line', source: 'route', paint: { 'line-color': '#ffffff', 'line-width': 9 }, layout: LINE_LAYOUT })
  map.addLayer({ id: 'route-line', type: 'line', source: 'route', paint: { 'line-color': '#e4572e', 'line-width': 5 }, layout: LINE_LAYOUT })
  map.addLayer({ id: 'segment-line', type: 'line', source: 'segment', paint: { 'line-color': '#2f5d46', 'line-width': 7 }, layout: LINE_LAYOUT })
}

const lineFeature = (coordinates: [number, number][]) => ({ ...EMPTY_LINE, geometry: { type: 'LineString' as const, coordinates } })

export function MapView(props: MapViewProps) {
  const { route, selectedSegment, places, pickMode, onMapClick } = props
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const clickRef = useRef(onMapClick)
  const selectRef = useRef(props.onSelectPlace)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    selectRef.current = props.onSelectPlace
  }, [props.onSelectPlace])

  useEffect(() => {
    clickRef.current = onMapClick
  }, [onMapClick])

  useEffect(() => {
    if (!containerRef.current) return
    const map = new maplibregl.Map({ container: containerRef.current, style: MAP_STYLE, center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.on('load', () => {
      addRouteLayers(map)
      setLoaded(true)
    })
    map.on('click', (e: MapMouseEvent) => clickRef.current({ lat: e.lngLat.lat, lon: e.lngLat.lng }))
    mapRef.current = map
    return () => map.remove()
  }, [])

  useEffect(() => {
    if (mapRef.current) mapRef.current.getCanvas().style.cursor = pickMode ? 'crosshair' : ''
  }, [pickMode])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded) return
    const coords = route?.geojson.coordinates ?? []
    ;(map.getSource('route') as GeoJSONSource).setData(lineFeature(coords))
    if (coords.length > 1) map.fitBounds(boundsOf(coords), { padding: FIT_PADDING, duration: 900 })
  }, [route, loaded])

  // Without a route, bring chosen places into view — but only when some are off-screen, so manual clicks don't move the map.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded || route || places.length === 0) return
    const coords = places.map((p): [number, number] => [p.lon, p.lat])
    const bounds = map.getBounds()
    if (coords.every((c) => bounds.contains(c))) return
    map.fitBounds(boundsOf(coords), { padding: FIT_PADDING, duration: 700, maxZoom: 13 })
  }, [places, route, loaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded) return
    const segment = route && selectedSegment !== null ? route.segments[selectedSegment] : null
    const coords =
      segment && route
        ? sliceLineByFraction(route.geojson.coordinates, segment.fromKm / route.distanceKm, segment.toKm / route.distanceKm)
        : []
    ;(map.getSource('segment') as GeoJSONSource).setData(lineFeature(coords))
    if (coords.length > 1) map.fitBounds(boundsOf(coords), { padding: FIT_PADDING, duration: 700, maxZoom: 14 })
  }, [route, selectedSegment, loaded])

  // Markers carry only plain data, so a JSON key is a cheap way to re-create them only when they change.
  const specsKey = JSON.stringify(markerSpecs(props).map(({ point, ...rest }) => ({ ...rest, point: { lat: point.lat, lon: point.lon } })))
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const markers = (JSON.parse(specsKey) as MarkerSpec[]).map((spec) =>
      new maplibregl.Marker({ element: markerElement(spec, (id) => selectRef.current(id)) })
        .setLngLat([spec.point.lon, spec.point.lat])
        .addTo(map),
    )
    return () => markers.forEach((m) => m.remove())
  }, [specsKey])

  // MapLibre's own CSS forces position:relative on the map element, so size it via a wrapper.
  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="size-full" aria-label="Route map" />
    </div>
  )
}
