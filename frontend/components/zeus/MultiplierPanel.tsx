'use client'

import { AnimatePresence } from 'motion/react'
import type { ZeusPageLabels } from '@/types/zeus'
import GlobalMultiplier from './GlobalMultiplier'
import MultiplierBadge from './MultiplierBadge'

interface MultiplierPanelProps {
  collected: number[]
  total: number
  inBonus: boolean
  labels: ZeusPageLabels
}

export default function MultiplierPanel({ collected, total, inBonus, labels }: MultiplierPanelProps) {
  return (
    <aside
      className={`flex-wrap items-center justify-center gap-3 rounded-2xl border border-border bg-surface/60 p-3 lg:flex lg:flex-col lg:items-stretch ${
        collected.length > 0 || inBonus ? 'flex' : 'hidden'
      }`}
    >
      <GlobalMultiplier value={total} inBonus={inBonus} label={labels.multiplier_total} />

      <p className="text-center text-xs text-muted">{labels.multiplier_collected}</p>

      <div className="flex flex-1 flex-wrap justify-center gap-1.5 lg:flex-none">
        <AnimatePresence>
          {collected.map((value, index) => (
            <MultiplierBadge key={index} multiplier={value} />
          ))}
        </AnimatePresence>
      </div>
    </aside>
  )
}
