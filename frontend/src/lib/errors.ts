const SAFE_PROTOCOLS = ['http:', 'https:']

/** External links come from the web (Exa, Wikimedia, users) — only allow http(s). */
export function safeUrl(url: string): string | undefined {
  try {
    return SAFE_PROTOCOLS.includes(new URL(url).protocol) ? url : undefined
  } catch {
    return undefined
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'Something went wrong. Please try again.'
}
