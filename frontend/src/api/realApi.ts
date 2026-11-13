import type { ApiClient } from '../types'

const API_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080'
const AGENT_URL = import.meta.env.VITE_AGENT_BASE_URL ?? 'http://localhost:8000'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`Request to ${url} failed (${res.status}): ${body.slice(0, 200)}`)
  }
  return (await res.json()) as T
}

const post = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) })

export const realApi: ApiClient = {
  chat: (req) => request(`${AGENT_URL}/api/chat`, post(req)),
  addPlace: (place) => request(`${API_URL}/api/places`, post(place)),
  createRoute: (req) => request(`${API_URL}/api/routes`, post(req)),
  getRoute: (id) => request(`${API_URL}/api/routes/${encodeURIComponent(id)}`),
  createItinerary: (req) => request(`${API_URL}/api/itineraries`, post(req)),
  getItinerary: (id) => request(`${API_URL}/api/itineraries/${encodeURIComponent(id)}`),
  replan: (id, req) => request(`${API_URL}/api/itineraries/${encodeURIComponent(id)}/replan`, post(req)),
}
