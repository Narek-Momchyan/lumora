'use client'

import { motion, useReducedMotion } from 'motion/react'
import type { Ref } from 'react'

interface OddsButtonProps {
  label?: string // "Bayern", "Draw", "Over 2.5"; a table cell has none
  stacked?: boolean // label over the price, for narrow columns
  odds: string // always a string with two decimals from the API, never a float
  trend?: 'up' | 'down' | null // the price moved since the last one (▲ / ▼)
  flash?: 'up' | 'down' | null // it moved just now: flashes green or red for a moment
  selected?: boolean // in the bet slip
  disabled?: boolean // the market is closed (kickoff)
  buttonRef?: Ref<HTMLButtonElement>
  onClick?: () => void
}

// One price of a market (designs 06, 07). Picked: lime with dark text and a glow, in both themes.
export default function OddsButton({
  label,
  stacked = false,
  odds,
  trend = null,
  flash = null,
  selected = false,
  disabled = false,
  buttonRef,
  onClick,
}: OddsButtonProps) {
  const reduce = useReducedMotion()
  const flashColor = flash === 'up' ? 'var(--color-lime)' : 'var(--color-danger)'

  return (
    <motion.button
      ref={buttonRef}
      type="button"
      aria-pressed={selected}
      disabled={disabled}
      onClick={onClick}
      // Animation 3: the price flashes for 2 s; animation 4: a picked price gives a short pulse.
      animate={
        reduce
          ? undefined
          : flash
            ? { boxShadow: [`0 0 0 0 transparent`, `0 0 0 2px ${flashColor}`, `0 0 0 0 transparent`] }
            : selected
              ? { scale: [1, 1.06, 1] }
              : { scale: 1 }
      }
      transition={flash ? { duration: 2, times: [0, 0.2, 1] } : { duration: 0.25 }}
      className={`relative flex w-full min-w-0 rounded-xl border px-3 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        stacked && label ? 'h-14 flex-col items-center justify-center gap-0.5' : 'h-11 items-center gap-2'
      } ${label && !stacked ? 'justify-between' : 'justify-center'} ${
        selected
          ? 'border-lime bg-lime text-bg shadow-lg shadow-lime/30'
          : 'border-border bg-surface2 text-text hover:enabled:border-accent/60'
      }`}
    >
      {label && (
        <span className={`max-w-full min-w-0 truncate ${stacked ? 'text-xs' : ''} ${selected ? 'text-bg/80' : 'text-muted'}`}>
          {label}
        </span>
      )}
      <span className="shrink-0 font-heading text-base font-bold tabular-nums">{odds}</span>
      {trend && (
        <span
          aria-hidden="true"
          className={`absolute top-0.5 right-1.5 text-[8px] leading-none ${
            trend === 'up' ? (selected ? 'text-bg' : 'text-lime') : selected ? 'text-bg' : 'text-danger'
          }`}
        >
          {trend === 'up' ? '▲' : '▼'}
        </span>
      )}
    </motion.button>
  )
}
