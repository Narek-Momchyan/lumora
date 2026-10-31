import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'
const ACCESS_COOKIE = process.env.AUTH_ACCESS_COOKIE ?? 'lumora_access'
const SESSION_COOKIE = process.env.AUTH_REFRESH_COOKIE ?? 'lumora_refresh'

function toLogin(request: NextRequest) {
  return NextResponse.redirect(new URL('/login', request.url))
}

// Server components can't set cookies, so an expired access token is renewed here, before the
// page renders. The new cookie goes to the browser and into this request.
async function refreshAccess(request: NextRequest) {
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
    return NextResponse.next() // Django is down: the page shows that on its own
  }

  if (response.status >= 500) return NextResponse.next()
  if (!response.ok) {
    const redirect = toLogin(request)
    redirect.cookies.delete(SESSION_COOKIE)
    return redirect
  }

  const setCookie = response.headers.getSetCookie().find((item) => item.startsWith(`${ACCESS_COOKIE}=`))
  if (!setCookie) return NextResponse.next()

  const headers = new Headers(request.headers)
  headers.set('cookie', `${request.headers.get('cookie')}; ${setCookie.split(';')[0]}`)
  const next = NextResponse.next({ request: { headers } })
  next.headers.append('set-cookie', setCookie)
  return next
}

// It only looks at the cookies: Django decides whether a token is valid, on every API request.
export async function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE)
  const onLogin = request.nextUrl.pathname === '/login'

  if (!hasSession && !onLogin) return toLogin(request)
  if (hasSession && onLogin) return NextResponse.redirect(new URL('/', request.url))
  if (hasSession && !request.cookies.has(ACCESS_COOKIE)) return refreshAccess(request)
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api/|media/|_next/|favicon\\.ico).*)'],
}
