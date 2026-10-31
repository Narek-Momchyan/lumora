'use client'

import { AnimatePresence, motion } from 'motion/react'
import type { ZeusPageLabels } from '@/types/zeus'

interface MultiplierPanelProps {
  collected: number[]
  total: number
  labels: ZeusPageLabels
}

export default function MultiplierPanel({ collected, total, labels }: MultiplierPanelProps) {
  return (
    <aside
      className={`flex-wrap items-center gap-2 rounded-2xl border border-border bg-surface p-3 lg:flex lg:flex-col lg:items-stretch ${
        collected.length > 0 ? 'flex' : 'hidden'
      }`}
    >
      <p className="text-xs text-muted">{labels.multiplier_collected}</p>

      <div className="flex flex-1 flex-wrap gap-1 lg:flex-none">
        <AnimatePresence>
          {collected.map((value, index) => (
            <motion.span
              key={index}
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ opacity: 0 }}
              className="rounded-lg bg-surface2 px-2 py-1 text-xs font-bold text-lime"
            >
              ×{value}
            </motion.span>
          ))}
        </AnimatePresence>
      </div>

      {total > 0 && (
        <p className="text-sm font-bold text-cyan lg:text-center">
          {labels.multiplier_total} ×{total}
        </p>
      )}
    </aside>
  )
}
