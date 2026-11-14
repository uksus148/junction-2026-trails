import { afterEach, describe, expect, it, vi } from 'vitest'
import { realApi } from './realApi'

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
