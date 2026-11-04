'use client'

import { useRef, useState } from 'react'
import type { RefObject } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Field from '@/components/ui/Field'
import { FIRST_AMOUNT, PLUS_STEP_CENTS, multiplierAt, payoutAt } from '@/lib/crash'
import { formatBalance, fromCents, toCents } from '@/lib/wallet'
import type { CrashPageLabels, CrashRound } from '@/types/crash'
import type { Game } from '@/types/game'
import useFlightFrame from './useFlightFrame'

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
        <Button
          size="lg"
          block
          disabled={pending}
          onClick={onCashOut}
          suffix={
            <>
              · <span ref={liveAmountRef} className="tabular-nums" /> {currency}
            </>
          }
        >
          {labels.cash_out}
        </Button>
      )
    }
    if (canBet) {
      return (
        <Button size="lg" block disabled={pending} onClick={() => onBet(amount, target)}>
          {labels.place_bet}
        </Button>
      )
    }

    let text = labels.waiting_status
    if (cashedAt) text = labels.cashed_out.replace('{multiplier}', cashedAt)
    else if (betAmount && round?.status === 'betting') text = labels.bet_placed
    return (
      <Button size="lg" block disabled>
        {text}
      </Button>
    )
  }

  const steps = [
    { label: labels.bet_half, cents: () => Math.floor(toCents(amount) / 2) },
    { label: labels.bet_double, cents: () => toCents(amount) * 2 },
    { label: labels.bet_plus, cents: () => toCents(amount) + PLUS_STEP_CENTS },
    { label: labels.bet_max, cents: () => Number.MAX_SAFE_INTEGER },
  ]

  return (
    <Card className="space-y-4">
      <Field
        id="crash-amount"
        label={labels.bet_amount}
        inputMode="decimal"
        autoComplete="off"
        value={amount}
        onChange={(event) => setAmount(event.target.value)}
      />

      <div className="grid grid-cols-4 gap-2">
        {steps.map(({ label, cents }) => (
          <Button key={label} variant="ghost" onClick={() => scaleAmount(cents())}>
            {label}
          </Button>
        ))}
      </div>

      <Field
        id="crash-target"
        label={labels.auto_cash_out_at}
        inputMode="decimal"
        autoComplete="off"
        value={target}
        onChange={(event) => setTarget(event.target.value)}
      />

      {mainButton()}

      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </Card>
  )
}
