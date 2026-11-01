'use client'

import { useRef, useState } from 'react'
import type { RefObject } from 'react'
import { FIRST_AMOUNT, PLUS_STEP_CENTS, multiplierAt, payoutAt } from '@/lib/crash'
import { formatBalance, fromCents, toCents } from '@/lib/wallet'
import type { CrashPageLabels, CrashRound } from '@/types/crash'
import type { Game } from '@/types/game'
import useFlightFrame from './useFlightFrame'

const INPUT =
  'w-full rounded-lg border border-border bg-surface2 px-3 py-2 text-sm text-text outline-none placeholder:text-muted focus:border-cyan'
const STEP_BUTTON =
  'rounded-lg border border-border bg-surface2 py-1.5 text-xs font-medium transition-colors hover:border-cyan'
const MAIN_BUTTON =
  'w-full truncate rounded-lg bg-linear-to-r from-cyan to-magenta px-3 py-2.5 text-sm font-semibold text-bg transition-opacity hover:opacity-90 disabled:opacity-40'

interface BetPanelProps {
  game: Game
  round: CrashRound | null
  connected: boolean
  clockOffset: RefObject<number | null>
  balance: string
  betAmount: string | null // the player's bet on this round
  cashedAt: string | null
  pending: boolean
  error: string
  currency: string
  labels: CrashPageLabels
  onBet: (amount: string, target: string) => void
  onCashOut: () => void
}

export default function BetPanel({
  game,
  round,
  connected,
  clockOffset,
  balance,
  betAmount,
  cashedAt,
  pending,
  error,
  currency,
  labels,
  onBet,
  onCashOut,
}: BetPanelProps) {
  const [amount, setAmount] = useState(FIRST_AMOUNT)
  const [target, setTarget] = useState('')
  const liveAmountRef = useRef<HTMLSpanElement>(null)

  const inFlight = connected && round?.status === 'flying'
  const canBet = connected && round?.status === 'betting' && !betAmount
  const canCashOut = inFlight && Boolean(betAmount) && !cashedAt

  useFlightFrame(round, clockOffset, (flight) => {
    if (liveAmountRef.current && betAmount) {
      liveAmountRef.current.textContent = formatBalance(payoutAt(betAmount, multiplierAt(flight)))
    }
  })

  function scaleAmount(cents: number) {
    const most = Math.min(toCents(balance), toCents(game.max_bet))
    setAmount(fromCents(Math.max(toCents(game.min_bet), Math.min(most, cents))))
  }

  function mainButton() {
    if (canCashOut) {
      return (
        <button type="button" disabled={pending} onClick={onCashOut} className={MAIN_BUTTON}>
          {labels.cash_out} · <span ref={liveAmountRef} className="tabular-nums" /> {currency}
        </button>
      )
    }
    if (canBet) {
      return (
        <button type="button" disabled={pending} onClick={() => onBet(amount, target)} className={MAIN_BUTTON}>
          {labels.place_bet}
        </button>
      )
    }

    let text = labels.waiting_status
    if (cashedAt) text = labels.cashed_out.replace('{multiplier}', cashedAt)
    else if (betAmount && round?.status === 'betting') text = labels.bet_placed
    return (
      <button type="button" disabled className={MAIN_BUTTON}>
        {text}
      </button>
    )
  }

  return (
    <section className="space-y-2.5 rounded-2xl border border-border bg-surface p-3">
      <div className="grid grid-cols-2 gap-2">
        <div className="min-w-0">
          <label htmlFor="crash-amount" className="mb-1 block truncate text-xs text-muted">
            {labels.bet_amount}
          </label>
          <input
            id="crash-amount"
            inputMode="decimal"
            autoComplete="off"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            className={INPUT}
          />
        </div>

        <div className="min-w-0">
          <label htmlFor="crash-target" className="mb-1 block truncate text-xs text-muted">
            {labels.auto_cash_out_at}
          </label>
          <input
            id="crash-target"
            inputMode="decimal"
            autoComplete="off"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
            className={INPUT}
          />
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2">
        <button type="button" onClick={() => scaleAmount(Math.floor(toCents(amount) / 2))} className={STEP_BUTTON}>
          {labels.bet_half}
        </button>
        <button type="button" onClick={() => scaleAmount(toCents(amount) * 2)} className={STEP_BUTTON}>
          {labels.bet_double}
        </button>
        <button type="button" onClick={() => scaleAmount(toCents(amount) + PLUS_STEP_CENTS)} className={STEP_BUTTON}>
          {labels.bet_plus}
        </button>
        <button type="button" onClick={() => scaleAmount(Number.MAX_SAFE_INTEGER)} className={STEP_BUTTON}>
          {labels.bet_max}
        </button>
      </div>

      {mainButton()}

      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </section>
  )
}
