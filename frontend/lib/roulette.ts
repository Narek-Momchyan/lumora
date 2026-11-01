import type { BetSpot, PocketColor, RoulettePageLabels } from '@/types/roulette'

export const GAME_SLUG = 'lumora-roulette'
export const WS_URL = process.env.NEXT_PUBLIC_ROULETTE_WS_URL ?? 'ws://127.0.0.1:8000/ws/roulette'
export const CHIPS = [1, 5, 10, 25, 100, 500]
export const FIRST_CHIP = 10
export const PAUSE_MS = 4000

// The same as backend/roulette/engine.py: the wheel clockwise, and the red numbers.
export const WHEEL = [
  0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7,
  28, 12, 35, 3, 26,
]
const RED = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36])

const MULTIPLIERS: Record<string, number> = {
  straight: 36,
  split: 18,
  street: 12,
  trio: 12,
  corner: 9,
  first_four: 9,
  six_line: 6,
  dozen: 3,
  column: 3,
}
const EVEN_MONEY = 2

export function colorOf(pocket: number): PocketColor {
  if (pocket === 0) return 'green'
  return RED.has(pocket) ? 'red' : 'black'
}

export function multiplierOf(betType: string) {
  return MULTIPLIERS[betType] ?? EVEN_MONEY
}

export function spotKey({ bet_type, value }: BetSpot) {
  return `${bet_type}:${value.join('/')}`
}

function spotName({ bet_type, value }: BetSpot, labels: RoulettePageLabels) {
  if (bet_type === 'dozen') return labels[`bet_dozen_${value[0]}` as 'bet_dozen_1']
  if (bet_type === 'column') return labels.bet_column.replace('{number}', String(value[0]))
  return labels[`bet_${bet_type}` as 'bet_red']
}

// "Split · 8 / 11", or only "Red".
export function spotLabel(spot: BetSpot, labels: RoulettePageLabels) {
  const name = spotName(spot, labels)
  const numbered = spot.bet_type !== 'dozen' && spot.bet_type !== 'column' && spot.value.length > 0
  return numbered ? `${name} · ${spot.value.join(' / ')}` : name
}

// ["Red · Odd", "19–36 · 2nd 12 · Column 2"], for the winning number.
export function resultLines(pocket: number, labels: RoulettePageLabels) {
  if (pocket === 0) return [labels.color_green, '']
  const color = RED.has(pocket) ? labels.bet_red : labels.bet_black
  const parity = pocket % 2 === 0 ? labels.bet_even : labels.bet_odd
  const half = pocket <= 18 ? labels.bet_low : labels.bet_high
  const dozen = spotName({ bet_type: 'dozen', value: [Math.ceil(pocket / 12)] }, labels)
  const column = spotName({ bet_type: 'column', value: [((pocket - 1) % 3) + 1] }, labels)
  return [`${color} · ${parity}`, `${half} · ${dozen} · ${column}`]
}
