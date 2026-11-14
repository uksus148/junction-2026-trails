import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, realApi } from './realApi'

function stubFetch(body: unknown) {
  const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify(body), { status: 200 }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const sentHeaders = (fetchMock: ReturnType<typeof stubFetch>) => new Headers(fetchMock.mock.calls[0][1]?.headers)

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('realApi', () => {
  it('sends GET requests without a Content-Type so browsers skip the CORS preflight', async () => {
    const fetchMock = stubFetch({ id: 'r1' })

    await realApi.getRoute('r1')

    expect(fetchMock.mock.calls[0][1]?.method ?? 'GET').toBe('GET')
    expect(sentHeaders(fetchMock).has('Content-Type')).toBe(false)
  })

  it('sends POST bodies as JSON', async () => {
    const fetchMock = stubFetch({ reply: 'ok', places: [] })

    await realApi.chat({ sessionId: 's', message: 'hi' })

    const init = fetchMock.mock.calls[0][1]
    expect(init?.method).toBe('POST')
    expect(sentHeaders(fetchMock).get('Content-Type')).toBe('application/json')
    expect(JSON.parse(String(init?.body))).toEqual({ sessionId: 's', message: 'hi' })
  })
})

describe('realApi errors', () => {
  function stubFailure(status: number, body: string, contentType = 'application/json') {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async () => new Response(body, { status, headers: { 'Content-Type': contentType } })))
  }

  it('shows the API Problem Details detail and keeps its code', async () => {
    stubFailure(422, JSON.stringify({ type: 'about:blank', title: 'No hiking route', status: 422, detail: 'No walking route connects the requested waypoints.', code: 'no_hiking_route' }), 'application/problem+json')

    const error = await realApi.getRoute('r1').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ message: 'No walking route connects the requested waypoints.', status: 422, code: 'no_hiking_route' })
  })

  it("shows the agent's FastAPI detail", async () => {
    stubFailure(503, JSON.stringify({ detail: 'Chat session storage is temporarily unavailable.' }))

    await expect(realApi.chat({ sessionId: 's', message: 'hi' })).rejects.toThrow('Chat session storage is temporarily unavailable.')
  })

  it('preserves a waypoint matching failure separately from a disconnected route', async () => {
    const detail = "One or more waypoints could not be matched to the available hiking network within the provider's search radius."
    stubFailure(422, JSON.stringify({ type: 'about:blank', title: 'Unprocessable Entity', status: 422, detail, code: 'waypoint_not_routable' }), 'application/problem+json')

    const error = await realApi.createRoute({ start: { lat: 49, lon: 20 }, end: { lat: 49.2, lon: 20.2 }, placeIds: [], preferences: [] }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ message: detail, status: 422, code: 'waypoint_not_routable' })
  })

  it('joins FastAPI validation messages', async () => {
    stubFailure(422, JSON.stringify({ detail: [{ loc: ['body', 'message'], msg: 'String should have at least 1 character', type: 'string_too_short' }] }))

    await expect(realApi.chat({ sessionId: 's', message: '' })).rejects.toThrow('String should have at least 1 character')
  })

  it('does not show raw HTML from a proxy error page', async () => {
    stubFailure(502, '<html><body>Bad Gateway</body></html>', 'text/html')

    await expect(realApi.getRoute('r1')).rejects.toThrow('Request failed (502). Please try again.')
  })
})
