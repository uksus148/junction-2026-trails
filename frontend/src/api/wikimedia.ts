import type { Photo } from '../types'

// Free, keyless: Wikimedia Commons geosearch for openly licensed photos near a point.
const COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
const SEARCH_RADIUS_M = 1500
const CANDIDATE_LIMIT = 30
const PHOTO_LIMIT = 6
const THUMB_WIDTH_PX = 640

type CommonsPage = {
  title: string
  coordinates?: { lat: number; lon: number }[]
  imageinfo?: {
    url: string
    thumburl?: string
    descriptionurl: string
    mime: string
    extmetadata?: Record<string, { value: string } | undefined>
  }[]
}

const stripHtml = (html: string) => html.replace(/<[^>]*>/g, '').trim()

function toPhoto(page: CommonsPage, fallback: { lat: number; lon: number }): Photo | null {
  const info = page.imageinfo?.[0]
  if (!info || info.mime !== 'image/jpeg') return null
  const meta = info.extmetadata ?? {}
  const coords = page.coordinates?.[0] ?? fallback
  return {
    url: info.url,
    thumbUrl: info.thumburl ?? info.url,
    author: stripHtml(meta.Artist?.value ?? 'Unknown author'),
    license: meta.LicenseShortName?.value ?? 'See source',
    sourceUrl: info.descriptionurl,
    lat: coords.lat,
    lon: coords.lon,
  }
}

export async function findPhotosNear(lat: number, lon: number): Promise<Photo[]> {
  const params = new URLSearchParams({
    action: 'query',
    format: 'json',
    origin: '*',
    generator: 'geosearch',
    ggscoord: `${lat}|${lon}`,
    ggsradius: String(SEARCH_RADIUS_M),
    ggslimit: String(CANDIDATE_LIMIT),
    ggsnamespace: '6',
    prop: 'imageinfo|coordinates',
    iiprop: 'url|mime|extmetadata',
    iiurlwidth: String(THUMB_WIDTH_PX),
  })
  const res = await fetch(`${COMMONS_API}?${params}`)
  if (!res.ok) throw new Error(`Wikimedia Commons request failed: ${res.status}`)
  const data = (await res.json()) as { query?: { pages?: Record<string, CommonsPage> } }
  const pages = Object.values(data.query?.pages ?? {})
  return pages
    .map((page) => toPhoto(page, { lat, lon }))
    .filter((photo): photo is Photo => photo !== null)
    .slice(0, PHOTO_LIMIT)
}
