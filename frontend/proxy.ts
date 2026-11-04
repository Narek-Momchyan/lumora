import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { DEFAULT_MODE, MODE_COOKIE, MODE_HEADER, isMode, modeForPath } from '@/lib/mode'
import type { Mode } from '@/lib/mode'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'
const ACCESS_COOKIE = process.env.AUTH_ACCESS_COOKIE ?? 'lumora_access'
const SESSION_COOKIE = process.env.AUTH_REFRESH_COOKIE ?? 'lumora_refresh'
const ONE_YEAR = 60 * 60 * 24 * 365

function toLogin(request: NextRequest) {
  return NextResponse.redirect(new URL('/login', request.url))
}

// Server components can't set cookies, so an expired access token is renewed here, before the
// page renders. The new cookie goes to the browser and into this request.
async function refreshAccess(request: NextRequest, headers: Headers) {
  let response: Response
  try {
    response = await fetch(`${BACKEND_URL}/api/token/refresh`, {
      method: 'POST',
      headers: {
        Cookie: request.headers.get('cookie') ?? '',
        Origin: request.nextUrl.origin,
        'X-CSRFToken': request.cookies.get('csrftoken')?.value ?? '',
      },
    })
  } catch {
    return NextResponse.next({ request: { headers } }) // Django is down: the page shows that on its own
  }

  if (response.status >= 500) return NextResponse.next({ request: { headers } })
  if (!response.ok) {
    const redirect = toLogin(request)
    redirect.cookies.delete(SESSION_COOKIE)
    return redirect
  }

  const setCookie = response.headers.getSetCookie().find((item) => item.startsWith(`${ACCESS_COOKIE}=`))
  if (!setCookie) return NextResponse.next({ request: { headers } })

  headers.set('cookie', `${request.headers.get('cookie')}; ${setCookie.split(';')[0]}`)
  const next = NextResponse.next({ request: { headers } })
  next.headers.append('set-cookie', setCookie)
  return next
}

// The page's section (Sports or Casino): its route decides, a shared page keeps the last one.
// The root layout reads it from the request header and sets <html data-theme>.
function pageMode(request: NextRequest): Mode {
  const saved = request.cookies.get(MODE_COOKIE)?.value
  return modeForPath(request.nextUrl.pathname) ?? (isMode(saved) ? saved : DEFAULT_MODE)
}

function rememberMode(response: NextResponse, mode: Mode) {
  response.cookies.set(MODE_COOKIE, mode, { path: '/', maxAge: ONE_YEAR, sameSite: 'lax' })
  return response
}

// It only looks at the cookies: Django decides whether a token is valid, on every API request.
export async function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE)
  const onLogin = request.nextUrl.pathname === '/login'

  if (!hasSession && !onLogin) return toLogin(request)
  if (hasSession && onLogin) return NextResponse.redirect(new URL('/', request.url))

  const mode = pageMode(request)
  const headers = new Headers(request.headers)
  headers.set(MODE_HEADER, mode)

  if (hasSession && !request.cookies.has(ACCESS_COOKIE)) {
    const response = await refreshAccess(request, headers)
    return response.headers.has('location') ? response : rememberMode(response, mode)
  }
  return rememberMode(NextResponse.next({ request: { headers } }), mode)
}

export const config = {
  matcher: ['/((?!api/|media/|_next/|favicon\\.ico).*)'],
}
