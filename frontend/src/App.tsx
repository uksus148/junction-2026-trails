import { useState } from 'react'
import { AlongTheWay } from './components/AlongTheWay'
import { DayTimeline } from './components/DayTimeline'
import { MapView } from './components/MapView'
import { PhotoViewer } from './components/PhotoViewer'
import { Sidebar } from './components/Sidebar'
import { useTrip } from './hooks/useTrip'
import type { Photo } from './types'

export default function App() {
  const trip = useTrip()
  const [openPhoto, setOpenPhoto] = useState<Photo | null>(null)
  const { itinerary } = trip.day
  const isDay = trip.mode === 'day'
  const mapRoute = isDay ? (itinerary?.route ?? null) : trip.route
  const doneIds = isDay && itinerary ? itinerary.stops.filter((s) => s.status === 'done').map((s) => s.place.id) : []

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      <Sidebar trip={trip} />
      <main className="relative min-h-0 flex-1">
        <MapView
          route={mapRoute}
          selectedSegment={isDay ? null : trip.selectedSegment}
          start={trip.start}
          end={isDay ? null : trip.end}
          places={trip.places}
          pendingPoint={trip.pendingPoint}
          pickMode={trip.pickMode}
          doneIds={doneIds}
          onMapClick={trip.handleMapClick}
        />
        {!isDay && trip.route && (
          <AlongTheWay route={trip.route} selectedSegment={trip.selectedSegment} onSelectSegment={trip.setSelectedSegment} onOpenPhoto={setOpenPhoto} />
        )}
        {isDay && itinerary && (
          <DayTimeline
            itinerary={itinerary}
            busy={trip.busy}
            onSkip={(id) => void trip.day.skipStop(id)}
            onDone={(id) => void trip.day.markDone(id)}
            onLate={(m) => void trip.day.runningLate(m)}
            onReplanNow={() => void trip.day.replanNow()}
            onOpenPhoto={setOpenPhoto}
          />
        )}
      </main>
      {openPhoto && <PhotoViewer photo={openPhoto} onClose={() => setOpenPhoto(null)} />}
    </div>
  )
}
