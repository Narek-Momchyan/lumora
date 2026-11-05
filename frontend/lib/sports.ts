import type { Match, MarketKind, SportsUiLabels, BetLabels, Team } from '@/types/sports'

// The same limits as backend sports/betting.py. The backend checks them again on every bet.
export const MIN_STAKE_CENTS = 100
export const MAX_STAKE_CENTS = 500_000
export const MAX_PICKS = 10
export const MAX_TOTAL_ODDS_CENTS = 100_000
export const MAX_WIN_CENTS = 10_000_000
export const STAKE_STEPS = [10, 50, 100]

export const POLL_SECONDS = 30
export const SLIP_STORAGE_KEY = 'lumora-slip'

export function fill(text: string, params: Record<string, string | number>) {
  return text.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? `{${name}}`))
}

// BigInt keeps odds × odds × stake exact (floats would drift). The tsconfig target has no 100n literals.
const ZERO = BigInt(0)
const HUNDRED = BigInt(100)

// "1.83" -> 183. Odds and money come as strings with two decimals; arithmetic is on whole cents.
export function toCentsExact(value: string) {
  const [whole, fraction = ''] = value.split('.')
  return BigInt(whole) * HUNDRED + BigInt((fraction + '00').slice(0, 2))
}

export function centsToString(cents: bigint) {
  const sign = cents < ZERO ? '-' : ''
  const abs = cents < ZERO ? -cents : cents
  return `${sign}${abs / HUNDRED}.${String(abs % HUNDRED).padStart(2, '0')}`
}

// Product of the odds, rounded down to 0.01 like the backend's Decimal (exact: BigInt).
export function totalOddsCents(odds: string[]) {
  if (odds.length === 0) return ZERO
  let product = BigInt(1)
  let scale = BigInt(1)
  odds.forEach((value, index) => {
    product *= toCentsExact(value)
    if (index > 0) scale *= HUNDRED
  })
  return product / scale
}

// stake (cents) × total odds (cents) / 100, rounded down: the potential win in cents.
export function potentialWinCents(stakeCents: bigint, totalCents: bigint) {
  return (stakeCents * totalCents) / HUNDRED
}

export function stakeToCents(stake: string) {
  return /^\d+(\.\d{0,2})?$/.test(stake.trim()) ? Number(toCentsExact(stake.trim())) : NaN
}

export function trend(odds: string, previous: string | null) {
  if (!previous || previous === odds) return null
  return Number(odds) > Number(previous) ? 'up' : 'down'
}

export function teamName(team: Pick<Team, 'name' | 'short_name'>) {
  return team.short_name || team.name
}

// The pick's name: "Bayern", "Draw", "Over 2.5", "Yes", "2-1".
export function pickName(
  kind: MarketKind,
  line: string | null,
  code: string,
  match: { home: Pick<Team, 'name' | 'short_name'>; away: Pick<Team, 'name' | 'short_name'> },
  bet: BetLabels,
) {
  switch (kind) {
    case '1x2':
      return code === 'home' ? teamName(match.home) : code === 'away' ? teamName(match.away) : bet.draw
    case 'double_chance':
      return code === '1X' ? bet.home_or_draw : code === 'X2' ? bet.draw_or_away : bet.home_or_away
    case 'total':
      return fill(code === 'over' ? bet.over : bet.under, { line: line ?? '' })
    case 'btts':
      return code === 'yes' ? bet.yes : bet.no
    case 'correct_score':
      return code === 'other' ? bet.other_score : code.replace('-', ' – ')
  }
}

export function marketName(kind: MarketKind, bet: BetLabels) {
  const names: Record<MarketKind, string> = {
    '1x2': bet.match_result,
    double_chance: bet.double_chance,
    total: bet.total_goals,
    btts: bet.both_teams_to_score,
    correct_score: bet.correct_score,
  }
  return names[kind]
}

// "20:30" in the browser's time zone, "Today" / "Tomorrow" or "08.11" for the date.
export function timeOf(kickoff: string) {
  const date = new Date(kickoff)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function dateOf(kickoff: string) {
  const date = new Date(kickoff)
  return `${String(date.getDate()).padStart(2, '0')}.${String(date.getMonth() + 1).padStart(2, '0')}`
}

export function dayWord(kickoff: string, labels: Pick<SportsUiLabels, 'today' | 'tomorrow'>, now = new Date()) {
  const date = new Date(kickoff)
  const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString()
  if (sameDay(date, now)) return labels.today
  const tomorrow = new Date(now)
  tomorrow.setDate(now.getDate() + 1)
  return sameDay(date, tomorrow) ? labels.tomorrow : dateOf(kickoff)
}

export function weekday(kickoff: string, labels: Pick<SportsUiLabels, 'weekdays_short'>) {
  const index = (new Date(kickoff).getDay() + 6) % 7 // Monday first
  return labels.weekdays_short.split(',')[index] ?? ''
}

// The UTC day string a ?date= filter wants, `offset` days after today.
export function utcDay(offset = 0, now = new Date()) {
  const day = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + offset))
  return day.toISOString().slice(0, 10)
}

export function secondsUntil(kickoff: string, now = Date.now()) {
  return Math.max(0, Math.floor((Date.parse(kickoff) - now) / 1000))
}

export function countdown(seconds: number) {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor((seconds % 3600) / 60))}:${pad(seconds % 60)}`
}

export function hasStarted(match: Pick<Match, 'kickoff' | 'status'>, now = Date.now()) {
  return match.status !== 'scheduled' || Date.parse(match.kickoff) <= now
}
