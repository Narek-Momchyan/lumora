import type { SpeedMode, WinStage, ZeusPageLabels } from '@/types/zeus'

export const GAME_SLUG = 'zeus-legacy'
export const BET_STEPS = ['0.20', '0.50', '1.00', '2.00', '5.00', '10.00', '20.00', '50.00', '100.00']
export const AUTO_SPIN_CHOICES = [10, 25, 50, 100]
export const BONUS_BUY_COST = 100

export const ROWS = 5
export const COLS = 6

// How long each part of a spin stays on screen, in milliseconds.
export const SPEEDS: Record<SpeedMode, { land: number; win: number; cascade: number; end: number; next: number }> = {
  normal: { land: 700, win: 1000, cascade: 900, end: 200, next: 1200 },
  turbo: { land: 400, win: 600, cascade: 400, end: 300, next: 400 },
  instant: { land: 100, win: 150, cascade: 100, end: 100, next: 100 },
}

// Times the bet, from the biggest. These only choose the overlay: the win comes from the backend.
const WIN_STAGES: [number, WinStage][] = [
  [200, 'win_max'],
  [100, 'win_ultra'],
  [50, 'win_mega'],
  [25, 'win_super'],
  [10, 'win_big'],
]

export function winStage(payout: string, amount: string) {
  const times = Number(payout) / Number(amount)
  return WIN_STAGES.find(([min]) => times >= min)?.[1] ?? null
}

// Whole cents, so the running win on screen has no float noise. The real win is `payout`.
export function payToLc(pay: number, amount: string) {
  const cents = Math.round(Number(amount) * 100)
  return (Math.floor((pay * cents) / 100) / 100).toFixed(2)
}

export function bonusCost(amount: string) {
  return (Math.round(Number(amount) * 100) * BONUS_BUY_COST) / 100
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
