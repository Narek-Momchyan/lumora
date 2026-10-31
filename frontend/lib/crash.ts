export const GAME_SLUG = 'neon-crash'
export const HISTORY_LENGTH = 20
export const GREEN_FROM = 2 // a crash point of 2x or more is shown in green
export const PLUS_STEP_CENTS = 10000
export const FIRST_AMOUNT = '100.00'

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://127.0.0.1:8000/ws/crash'
export const RECONNECT_MIN_MS = 500
export const RECONNECT_MAX_MS = 5000

const GROWTH_PER_MS = 0.00006
const MAX_MULTIPLIER = 1_000_000

// The same formula as multiplier_at in backend/crash/engine.py.
export function multiplierAt(ms: number) {
  if (ms <= 0) return 1
  return Math.min(MAX_MULTIPLIER, Math.floor(100 * Math.exp(GROWTH_PER_MS * ms)) / 100)
}

// The exact curve, before flooring: it draws the line.
export function curveAt(ms: number) {
  return Math.exp(GROWTH_PER_MS * ms)
}

export function flightMs(multiplier: number) {
  return Math.log(multiplier) / GROWTH_PER_MS
}

export function toCents(amount: string) {
  return Math.round(Number(amount) * 100)
}

export function fromCents(cents: number) {
  return (cents / 100).toFixed(2)
}

// Whole cents and rounded down, as in the backend. The real payout comes from the server.
export function payoutAt(amount: string, multiplier: number) {
  return fromCents(Math.floor((toCents(amount) * Math.round(multiplier * 100)) / 100))
}
