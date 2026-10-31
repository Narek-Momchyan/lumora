'use client'

import { formatBalance } from '@/lib/wallet'
import type { SpeedMode, ZeusPageLabels } from '@/types/zeus'
import AutoplayMenu from './AutoplayMenu'

interface ControlBarProps {
  amount: string
  canLower: boolean
  canRaise: boolean
  winText: string | null
  isPlaying: boolean
  inBonus: boolean
  multiplier: number
  speed: SpeedMode
  autoLeft: number
  canBuyBonus: boolean
  bonusPrice: string
  currency: string
  labels: ZeusPageLabels
  onLower: () => void
  onRaise: () => void
  onSpeed: (speed: SpeedMode) => void
  onSpin: () => void
  onSkip: () => void
  onBuyBonus: () => void
  onAutoStart: (spins: number) => void
  onAutoStop: () => void
}

const SPEEDS: SpeedMode[] = ['normal', 'turbo', 'instant']

export default function ControlBar(props: ControlBarProps) {
  const { amount, winText, isPlaying, inBonus, multiplier, speed, autoLeft, currency, labels } = props
  const speedLabels = { normal: labels.speed_normal, turbo: labels.speed_turbo, instant: labels.speed_instant }
  const betButton =
    'size-9 rounded-lg border border-border bg-surface2 text-lg font-bold text-text hover:border-muted disabled:opacity-40'

  return (
    <section className="space-y-2 rounded-2xl border border-border bg-surface p-2 sm:space-y-3 sm:p-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3">
        <div>
          <p className="text-xs text-muted">{inBonus ? labels.bonus_bet : labels.bet}</p>
          {inBonus ? (
            <p className="py-1.5 font-heading font-bold text-lime">{multiplier}</p>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label={labels.bet_lower}
                disabled={!props.canLower || isPlaying || autoLeft > 0}
                onClick={props.onLower}
                className={betButton}
              >
                −
              </button>
              <p className="min-w-16 text-center font-heading font-bold">
                {formatBalance(amount)} {currency}
              </p>
              <button
                type="button"
                aria-label={labels.bet_raise}
                disabled={!props.canRaise || isPlaying || autoLeft > 0}
                onClick={props.onRaise}
                className={betButton}
              >
                +
              </button>
            </div>
          )}
        </div>

        <div aria-live="polite">
          <p className="text-xs text-muted">{isPlaying ? labels.win : labels.last_win}</p>
          <p className="py-1.5 font-heading font-bold text-cyan">
            {winText ? `${formatBalance(winText)} ${currency}` : ''}
          </p>
        </div>

        <div className="col-span-2 sm:col-span-1">
          <p className="mb-1 hidden text-xs text-muted sm:block">{labels.speed_mode}</p>
          <div className="grid grid-cols-3 gap-1">
            {SPEEDS.map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={speed === mode}
                onClick={() => props.onSpeed(mode)}
                className={`truncate rounded-lg px-1 py-2 text-xs font-semibold transition-colors ${
                  speed === mode ? 'bg-text text-bg' : 'bg-surface2 text-muted hover:text-text'
                }`}
              >
                {speedLabels[mode]}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-[1fr_1fr_2fr]">
        <button
          type="button"
          disabled={!props.canBuyBonus || isPlaying || autoLeft > 0}
          onClick={props.onBuyBonus}
          className="rounded-xl border border-magenta px-3 py-2 text-sm font-semibold text-text transition-colors hover:bg-surface2 disabled:opacity-40"
        >
          {labels.buy_bonus}
          <span className="block text-xs text-muted">
            {props.bonusPrice} {currency}
          </span>
        </button>

        <AutoplayMenu
          autoLeft={autoLeft}
          disabled={isPlaying}
          labels={labels}
          onStart={props.onAutoStart}
          onStop={props.onAutoStop}
        />

        <button
          type="button"
          onClick={isPlaying ? props.onSkip : props.onSpin}
          disabled={autoLeft > 0 && !isPlaying}
          className="col-span-2 rounded-xl bg-linear-to-r from-cyan to-magenta px-4 py-3 font-heading font-bold text-bg shadow-lg shadow-cyan/20 transition-opacity hover:opacity-90 disabled:opacity-60 sm:col-span-1"
        >
          {isPlaying ? labels.skip : labels.spin}
        </button>
      </div>
    </section>
  )
}
