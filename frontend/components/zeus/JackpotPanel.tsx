'use client'

import { motion } from 'motion/react'
import { formatBalance } from '@/lib/wallet'
import { jackpotLabel } from '@/lib/zeus'
import type { ZeusPageLabels } from '@/types/zeus'

const TIERS = [
  { tier: 'GRAND', color: 'var(--color-zeus-yellow)' },
  { tier: 'MAJOR', color: 'var(--color-zeus-red)' },
  { tier: 'MINOR', color: 'var(--color-zeus-purple)' },
  { tier: 'MINI', color: 'var(--color-zeus-sky)' },
]

interface JackpotPanelProps {
  pools: Record<string, string>
  currency: string
  labels: ZeusPageLabels
}

export default function JackpotPanel({ pools, currency, labels }: JackpotPanelProps) {
  return (
    <section aria-label={labels.jackpots_label} className="grid grid-cols-4 gap-1 sm:gap-2">
      {TIERS.map(({ tier, color }) => (
        <motion.div
          key={tier}
          animate={{ boxShadow: [`0 0 3px ${color}`, `0 0 12px ${color}`, `0 0 3px ${color}`] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="min-w-0 rounded-xl px-1 py-1.5 text-center sm:px-3 sm:py-2"
          style={{
            border: `1px solid color-mix(in srgb, ${color} 19%, transparent)`,
            background: `color-mix(in srgb, ${color} 3%, transparent)`,
          }}
        >
          <p className="truncate text-[10px] font-black tracking-widest uppercase opacity-80 sm:text-xs" style={{ color }}>
            {jackpotLabel(tier, labels)}
          </p>
          <motion.p
            key={pools[tier]}
            initial={{ scale: 1.1 }}
            animate={{ scale: 1 }}
            className="truncate font-heading text-[11px] font-black text-zeus-white sm:text-base"
            style={{ textShadow: `0 0 12px ${color}` }}
          >
            {pools[tier] ? formatBalance(pools[tier]) : ''}
            <span className="hidden sm:inline"> {currency}</span>
          </motion.p>
        </motion.div>
      ))}
    </section>
  )
}
