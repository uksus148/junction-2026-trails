import type { Route } from '../types'

/** True when at least one segment has a photo. Routes may arrive with empty segments before the photo pipeline exists. */
export function routeHasPhotos(route: Route): boolean {
  return route.segments.some((segment) => segment.photos.length > 0)
}
