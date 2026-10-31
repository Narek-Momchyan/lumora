import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const SESSION_COOKIE = process.env.AUTH_REFRESH_COOKIE ?? 'lumora_refresh'

// A quick check before the page renders. It only looks for the cookie: Django decides
// whether the token inside is valid, on every API request.
export function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE)
  const onLogin = request.nextUrl.pathname === '/login'

  if (!hasSession && !onLogin) return NextResponse.redirect(new URL('/login', request.url))
  if (hasSession && onLogin) return NextResponse.redirect(new URL('/', request.url))
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api/|media/|_next/|favicon\\.ico).*)'],
}
