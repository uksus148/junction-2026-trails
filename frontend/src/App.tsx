import { useState } from 'react'
import { AlongTheWay } from './components/AlongTheWay'
import { MapView } from './components/MapView'
import { PhotoViewer } from './components/PhotoViewer'
import { Sidebar } from './components/Sidebar'
import { useTrip } from './hooks/useTrip'
import type { Photo } from './types'

export default function App() {
  const trip = useTrip()
  const [openPhoto, setOpenPhoto] = useState<Photo | null>(null)

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      <Sidebar trip={trip} />
      <main className="relative min-h-0 flex-1">
        <MapView
          route={trip.route}
          selectedSegment={trip.selectedSegment}
          start={trip.start}
          end={trip.end}
          places={trip.places}
          pendingPoint={trip.pendingPoint}
          pickMode={trip.pickMode}
          onMapClick={trip.handleMapClick}
        />
        {trip.route && (
          <AlongTheWay route={trip.route} selectedSegment={trip.selectedSegment} onSelectSegment={trip.setSelectedSegment} onOpenPhoto={setOpenPhoto} />
        )}
      </main>
      {openPhoto && <PhotoViewer photo={openPhoto} onClose={() => setOpenPhoto(null)} />}
    </div>
  )
}
