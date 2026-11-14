import { useEffect } from 'react'
import { safeUrl } from '../lib/errors'
import type { Photo } from '../types'

interface PhotoViewerProps {
  photo: Photo
  onClose: () => void
}

export function PhotoViewer({ photo, onClose }: PhotoViewerProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" onClick={onClose}>
      <figure className="max-h-full max-w-5xl overflow-hidden rounded-2xl bg-paper shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <img src={photo.thumbUrl} alt={`View photographed by ${photo.author}`} className="max-h-[75vh] w-full bg-ink object-contain" />
        <figcaption className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
          <span className="text-stone">
            © {photo.author} · {photo.license}
          </span>
          <span className="flex gap-4">
            <a href={safeUrl(photo.sourceUrl)} target="_blank" rel="noopener noreferrer" className="font-medium text-moss hover:underline">
              Source ↗
            </a>
            <button onClick={onClose} className="font-medium text-ink hover:underline">
              Close
            </button>
          </span>
        </figcaption>
      </figure>
    </div>
  )
}
