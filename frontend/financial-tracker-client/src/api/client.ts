import { API_URL } from "./config";

export class AuthError extends Error {
    constructor(message = "Unauthorized") {
        super(message)
        this.name = "AuthError"
    }
}

// Its own error type for the same reason AuthError is one: a 429 needs a different
// reaction from a generic failure. Without this a rate-limited request falls into the
// "Request failed: 429" branch below, which every page swallows into console.error —
// so the user taps the button, nothing happens, and nothing explains why.
export class RateLimitError extends Error {
    constructor(message = "Too many requests. Please wait a bit and try again.") {
        super(message)
        this.name = "RateLimitError"
    }
}

// The backend's 429 handler always sends {"detail": "<string>"}, so this only needs
// the string case — the richer 422 parsing in api/auth.ts does not apply here.
async function rateLimitMessage(response: Response): Promise<string | undefined> {
    const data = await response.json().catch(() => null)
    if (typeof data === "object" && data !== null && "detail" in data) {
        const detail = (data as { detail: unknown }).detail
        if (typeof detail === "string") {
            return detail
        }
    }
    return undefined
}

export async function apiFetch(
  path: string,
  token: string | null,
  options: RequestInit = {}
): Promise<Response> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (response.status === 401) {
    throw new AuthError()
  }

  if (response.status === 429) {
    throw new RateLimitError(await rateLimitMessage(response))
  }

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }

  return response
}