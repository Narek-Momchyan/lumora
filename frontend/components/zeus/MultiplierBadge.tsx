'use client'

import { motion } from 'motion/react'

function badgeColor(multiplier: number) {
  if (multiplier >= 50) return 'var(--color-zeus-red)'
  if (multiplier >= 10) return 'var(--color-zeus-orange)'
  if (multiplier >= 5) return 'var(--color-zeus-lilac)'
  return 'var(--color-zeus-ice)'
}

function tint(color: string, percent: number) {
  return `color-mix(in srgb, ${color} ${percent}%, transparent)`
}

export default function MultiplierBadge({ multiplier }: { multiplier: number }) {
  const color = badgeColor(multiplier)

  return (
    <motion.div
      initial={{ scale: 0, x: -20, opacity: 0 }}
      animate={{ scale: 1, x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 240, damping: 18 }}
      className="relative flex items-center justify-center"
    >
      <div className="absolute -inset-1 rounded-full opacity-15 blur-sm" style={{ background: color }} />

      <div
        className="relative flex items-center gap-1 rounded-full px-3.5 py-1.5"
        style={{
          background: `linear-gradient(135deg, ${tint(color, 13)}, ${tint(color, 27)})`,
          border: `1px solid ${tint(color, 53)}`,
          boxShadow: `0 0 12px ${tint(color, 27)}`,
        }}
      >
        <span
          className="font-heading text-sm font-black italic"
          style={{ color, filter: `drop-shadow(0 0 6px ${color})` }}
        >
          ×{multiplier}
        </span>
        <motion.span
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1.2, repeat: Infinity }}
          className="text-xs leading-none"
          style={{ color }}
        >
          ✦
        </motion.span>
      </div>
    </motion.div>
  )
}
