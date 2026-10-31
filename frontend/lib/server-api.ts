import { cookies } from 'next/headers'
import { ApiError, parseResponse } from './api'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'

// For server components: calls Django directly and forwards the visitor's cookies.
export async function serverFetch<T>(path: string) {
  const cookieStore = await cookies()

  let response: Response
  try {
    response = await fetch(`${BACKEND_URL}/api${path}`, {
      cache: 'no-store',
      headers: { Cookie: cookieStore.toString() },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server.')
  }

  return parseResponse<T>(response)
}
