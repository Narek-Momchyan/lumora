import { cookies, headers } from 'next/headers'
import { DEFAULT_MODE, MODE_COOKIE, MODE_HEADER, isMode } from './mode'
import type { Mode } from './mode'

// The section of the page being rendered. proxy.ts puts it in a request header (the cookie it
// sets reaches the browser only with this response); the cookie is the fallback.
export async function displayMode(): Promise<Mode> {
  const fromProxy = (await headers()).get(MODE_HEADER)
  if (isMode(fromProxy)) return fromProxy

  const fromCookie = (await cookies()).get(MODE_COOKIE)?.value
  return isMode(fromCookie) ? fromCookie : DEFAULT_MODE
}
