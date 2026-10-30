const BASE_URL = process.env.NEXT_PUBLIC_API_URL
const ACCESS_KEY = 'lumora.access'
const REFRESH_KEY = 'lumora.refresh'

type ErrorData = Record<string, unknown> | null

interface FetchOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  // false for login and register: their 401 is a wrong password, not an expired token
  auth?: boolean
}

interface TokenPair {
  access: string
  refresh: string
}

// status 0 means the server could not be reached. `data` keeps the whole error
// body, for field errors ({"email": ["..."]}) and extras like `available_at`.
export class ApiError extends Error {
  status: number
  data: ErrorData

  constructor(status: number, message: string, data: ErrorData = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

// Tokens exist only in the browser, so on the server these return null and
// requests go out without a JWT.
function readToken(key: string) {
  return typeof window === 'undefined' ? null : localStorage.getItem(key)
}

export function saveTokens({ access, refresh }: TokenPair) {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export function isLoggedIn() {
  return readToken(REFRESH_KEY) !== null
}

async function send(path: string, init: RequestInit) {
  try {
    return await fetch(`${BASE_URL}${path}`, init)
  } catch {
    throw new ApiError(0, 'Cannot reach the server.')
  }
}

async function readBody(response: Response): Promise<ErrorData> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function errorMessage(status: number, data: ErrorData) {
  if (typeof data?.detail === 'string') return data.detail
  const first = Object.values(data ?? {})[0]
  if (Array.isArray(first) && typeof first[0] === 'string') return first[0]
  return `Request failed (${status}).`
}

async function refreshAccess() {
  const refresh = readToken(REFRESH_KEY)
  if (!refresh) return null

  const response = await send('/token/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!response.ok) {
    clearTokens()
    return null
  }

  const { access } = (await response.json()) as { access: string }
  localStorage.setItem(ACCESS_KEY, access)
  return access
}

// A page can start several requests at once: they all share one refresh.
let refreshing: Promise<string | null> | null = null

function refreshOnce() {
  refreshing ??= refreshAccess().finally(() => {
    refreshing = null
  })
  return refreshing
}

export async function apiFetch<T>(
  path: string,
  { body, auth = true, headers, ...init }: FetchOptions = {},
): Promise<T> {
  const request = (token: string | null) =>
    send(path, {
      ...init,
      headers: {
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...(token && { Authorization: `Bearer ${token}` }),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })

  const token = auth ? readToken(ACCESS_KEY) : null
  let response = await request(token)

  // Public endpoints also answer 401 to a bad token. If the refresh fails the
  // retry goes out without a token, so they still work for a logged-out player.
  if (response.status === 401 && token) {
    response = await request(await refreshOnce())
  }

  const data = await readBody(response)
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(response.status, data), data)
  }
  return data as T
}

export async function login(email: string, password: string) {
  const tokens = await apiFetch<TokenPair>('/token', {
    method: 'POST',
    body: { email, password },
    auth: false,
  })
  saveTokens(tokens)
}
