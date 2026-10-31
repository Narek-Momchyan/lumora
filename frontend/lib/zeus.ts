import type { SpeedMode, ZeusPageLabels } from '@/types/zeus'

export const GAME_SLUG = 'zeus-legacy'
export const BET_STEPS = ['0.20', '0.50', '1.00', '2.00', '5.00', '10.00', '20.00', '50.00', '100.00']
export const AUTO_SPIN_CHOICES = [10, 25, 50, 100]
export const BONUS_BUY_COST = 100

export const ROWS = 5
export const COLS = 6
export const FIRST_GRID = Array.from({ length: ROWS }, () => Array<string>(COLS).fill('blue_stone'))

export const BIG_WIN_PAY = 1000 // 10x: pays are in hundredths of the bet
export const SHAKE_MS = 300
export const LIGHTNING_MS = 800
export const SCATTER_SOUND_DELAY_MS = 300
export const SPIN_COOLDOWN_MS = 500
export const BONUS_END_MS = 1500
export const AUTO_CLOSE_MS = 4000
export const TEASER_MS = 2500

// How long each part of a spin stays on screen, in milliseconds. `overlay` shortens the overlays.
export const SPEEDS: Record<
  SpeedMode,
  { land: number; win: number; cascade: number; end: number; next: number; overlay: number }
> = {
  normal: { land: 700, win: 1000, cascade: 900, end: 200, next: 1200, overlay: 1 },
  turbo: { land: 400, win: 600, cascade: 400, end: 150, next: 400, overlay: 0.5 },
  instant: { land: 100, win: 150, cascade: 100, end: 100, next: 100, overlay: 0.2 },
}

const MULTIPLIER_COLORS: Record<string, string> = {
  mult_2: 'var(--color-zeus-mult-blue)',
  mult_5: 'var(--color-zeus-purple)',
  mult_10: 'var(--color-zeus-orange)',
  mult_25: 'var(--color-zeus-green)',
  mult_50: 'var(--color-zeus-red)',
  mult_100: 'var(--color-zeus-pink)',
  mult_250: 'var(--color-zeus-violet)',
  mult_500: 'var(--color-zeus-yellow)',
}

export function multiplierColor(code: string) {
  return MULTIPLIER_COLORS[code]
}

// A 4th scatter is near: every column after the third scatter waits a little longer.
export function teaserColumns(grid: string[][]) {
  const inColumn = Array.from({ length: COLS }, (_, col) => grid.filter((row) => row[col] === 'scatter').length)
  let scatters = 0
  let delay = 0
  return inColumn.map((count) => {
    const column = { teasing: scatters >= 3, delay }
    if (scatters >= 3) delay += TEASER_MS
    scatters += count
    return column
  })
}

export function teaserDelay(grid: string[][]) {
  const last = teaserColumns(grid)[COLS - 1]
  return last.delay + (last.teasing ? TEASER_MS : 0)
}

// Whole cents, so the running win on screen has no float noise. The real win is `payout`.
export function payToLc(pay: number, amount: string) {
  const cents = Math.round(Number(amount) * 100)
  return (Math.floor((pay * cents) / 100) / 100).toFixed(2)
}

export function bonusCost(amount: string) {
  return (Math.round(Number(amount) * 100) * BONUS_BUY_COST) / 100
}

export function formatCount(value: number, precision = 2) {
  return value.toLocaleString('en-US', { minimumFractionDigits: precision, maximumFractionDigits: precision })
}

export function jackpotLabel(tier: string, labels: ZeusPageLabels) {
  const names: Record<string, string> = {
    MINI: labels.jackpot_mini,
    MINOR: labels.jackpot_minor,
    MAJOR: labels.jackpot_major,
    GRAND: labels.jackpot_grand,
  }
  return names[tier] ?? tier
}
