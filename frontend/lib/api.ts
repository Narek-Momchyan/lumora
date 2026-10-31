import type { Player } from '@/types/account'

const CSRF_COOKIE = 'csrftoken'

type ErrorData = Record<string, unknown> | null

export type FieldErrors = Record<string, string[]>

interface FetchOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  // false for login and register: their 401 is a wrong password, not an expired session
  auth?: boolean
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

// {"email": ["..."], "detail": "..."} -> {email: ["..."]}
export function fieldErrors(error: ApiError) {
  const errors: FieldErrors = {}
  for (const [field, value] of Object.entries(error.data ?? {})) {
    if (Array.isArray(value)) errors[field] = value.map(String)
  }
  return errors
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

export async function parseResponse<T>(response: Response) {
  const data = await readBody(response)
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(response.status, data), data)
  }
  return data as T
}

async function send(path: string, init: RequestInit) {
  try {
    return await fetch(`/api${path}`, init)
  } catch {
    throw new ApiError(0, 'Cannot reach the server.')
  }
}

// Django's CSRF cookie is the only one JavaScript can read. The JWT cookies are httpOnly.
function csrfHeader(): Record<string, string> {
  const cookie = document.cookie.split('; ').find((item) => item.startsWith(`${CSRF_COOKIE}=`))
  return cookie ? { 'X-CSRFToken': cookie.slice(CSRF_COOKIE.length + 1) } : {}
}

async function refreshSession() {
  const response = await send('/token/refresh', { method: 'POST', headers: csrfHeader() })
  return response.ok
}

// A page can start several requests at once: they all share one refresh.
let refreshing: Promise<boolean> | null = null

function refreshOnce() {
  refreshing ??= refreshSession().finally(() => {
    refreshing = null
  })
  return refreshing
}

// For the browser only: server components use serverFetch from lib/server-api.ts.
export async function apiFetch<T>(
  path: string,
  { body, auth = true, headers, ...init }: FetchOptions = {},
): Promise<T> {
  const request = () =>
    send(path, {
      ...init,
      headers: {
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...csrfHeader(),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })

  let response = await request()

  // If the refresh fails, the caller gets this 401: it means "send to login".
  if (response.status === 401 && auth && (await refreshOnce())) {
    response = await request()
  }

  return parseResponse<T>(response)
}

export function login(email: string, password: string) {
  return apiFetch<Player>('/token', { method: 'POST', body: { email, password }, auth: false })
}
