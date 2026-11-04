// The site has two sections: Sports (football, the green theme) and Casino (the neon theme).
// The route decides the section; shared pages (Wallet, Leaderboard) keep the last one.
export type Mode = 'sports' | 'casino'

export const MODE_COOKIE = 'mode'
export const MODE_HEADER = 'x-lumora-mode'
export const DEFAULT_MODE: Mode = 'sports' // Lumora is football first

// Where the Sports | Casino switch takes the player.
export const MODE_HOME: Record<Mode, string> = { sports: '/', casino: '/casino' }

const CASINO_PATHS = ['/casino', '/crash', '/zeus-legacy', '/roulette', '/login']
const SPORTS_PATHS = ['/live', '/leagues', '/matches', '/my-bets', '/predictions', '/forums']

function startsWithPath(pathname: string, base: string) {
  return pathname === base || pathname.startsWith(`${base}/`)
}

export function modeForPath(pathname: string): Mode | null {
  if (CASINO_PATHS.some((base) => startsWithPath(pathname, base))) return 'casino'
  if (pathname === '/' || SPORTS_PATHS.some((base) => startsWithPath(pathname, base))) return 'sports'
  return null
}

export function isMode(value: string | undefined | null): value is Mode {
  return value === 'sports' || value === 'casino'
}
