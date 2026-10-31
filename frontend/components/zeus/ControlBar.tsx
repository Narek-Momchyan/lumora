'use client'

import { motion } from 'motion/react'
import { useState } from 'react'
import { formatBalance } from '@/lib/wallet'
import type { SpeedMode, ZeusPageLabels } from '@/types/zeus'
import AnimatedNumber from './AnimatedNumber'
import AutoplayMenu from './AutoplayMenu'

interface ControlBarProps {
  amount: string
  canLower: boolean
  canRaise: boolean
  winText: string | null
  isPlaying: boolean
  awaitingSpin: boolean
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
  onBuyBonus: () => void
  onAutoStart: (spins: number) => void
  onAutoStop: () => void
}

const SPEEDS: SpeedMode[] = ['normal', 'turbo', 'instant']

// Pops on every new win and counts up from the one before it.
function WinValue({ value, currency }: { value: number; currency: string }) {
  const [shown, setShown] = useState({ value, from: 0 })
  if (shown.value !== value) setShown({ value, from: shown.value })

  return (
    <motion.p
      key={value}
      initial={{ scale: 0.7, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 350, damping: 20 }}
      className="py-1.5 font-heading font-bold text-zeus-gold"
      style={{ filter: 'drop-shadow(0 0 10px var(--color-zeus-gold))' }}
    >
      +<AnimatedNumber value={value} from={shown.from} /> {currency}
    </motion.p>
  )
}

export default function ControlBar(props: ControlBarProps) {
  const { amount, winText, isPlaying, inBonus, multiplier, speed, autoLeft, currency, labels } = props
  const speedLabels = { normal: labels.speed_normal, turbo: labels.speed_turbo, instant: labels.speed_instant }
  const canBuy = props.canBuyBonus && !isPlaying && autoLeft === 0
  const betButton =
    'size-9 rounded-lg border border-border bg-surface2 text-lg font-bold text-text hover:border-muted disabled:opacity-40'

  return (
    <section className="space-y-2 rounded-2xl border border-border bg-surface/80 p-2 sm:space-y-3 sm:p-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3">
        <div>
          <p className="text-xs text-muted">{inBonus ? labels.bonus_bet : labels.bet}</p>
          {inBonus ? (
            <p className="py-1.5 font-heading font-bold text-zeus-lilac">
              <AnimatedNumber value={multiplier} precision={0} />
            </p>
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

        <div
          aria-live="polite"
          className={`relative overflow-hidden rounded-lg px-2 ${winText ? 'bg-zeus-gold/10' : ''}`}
        >
          <p className="text-xs text-muted">{isPlaying ? labels.win : labels.last_win}</p>
          {winText ? <WinValue value={Number(winText)} currency={currency} /> : <p className="py-1.5 text-muted">—</p>}

          {!isPlaying && winText && (
            <motion.div
              key={winText}
              initial={{ opacity: 0.45 }}
              animate={{ opacity: 0 }}
              transition={{ duration: 0.9 }}
              className="pointer-events-none absolute inset-0 bg-zeus-gold/15"
            />
          )}
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
        <motion.button
          type="button"
          whileHover={canBuy ? { scale: 1.02 } : undefined}
          whileTap={canBuy ? { scale: 0.95 } : undefined}
          disabled={!canBuy}
          onClick={props.onBuyBonus}
          className="rounded-xl border border-zeus-purple/50 bg-zeus-purple/20 px-3 py-2 text-sm font-semibold text-text shadow-lg shadow-zeus-purple/30 disabled:opacity-40 disabled:shadow-none"
        >
          {labels.buy_bonus}
          <span className="block text-xs text-zeus-lilac-light">
            {props.bonusPrice} {currency}
          </span>
        </motion.button>

        <AutoplayMenu
          autoLeft={autoLeft}
          disabled={isPlaying}
          labels={labels}
          onStart={props.onAutoStart}
          onStop={props.onAutoStop}
        />

        <motion.button
          type="button"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.975 }}
          onClick={props.onSpin}
          disabled={autoLeft > 0 && !isPlaying}
          className={`col-span-2 rounded-xl px-4 py-3 font-heading disabled:opacity-60 sm:col-span-1 ${
            inBonus ? 'zeus-btn-bonus' : 'zeus-btn-spin'
          }`}
        >
          {isPlaying && !props.awaitingSpin ? labels.skip : labels.spin}
        </motion.button>
      </div>
    </section>
  )
}
