'use client'

import { AnimatePresence, motion } from 'motion/react'
import { useId } from 'react'

interface GlobalMultiplierProps {
  value: number
  inBonus: boolean
  label: string
}

export default function GlobalMultiplier({ value, inBonus, label }: GlobalMultiplierProps) {
  const boltId = useId()
  if (!inBonus && value <= 0) return null

  const accent = inBonus ? 'var(--color-zeus-lilac)' : 'var(--color-zeus-gold)'
  const glow = inBonus ? 'var(--color-zeus-purple)' : 'var(--color-zeus-gold)'
  const tint = (percent: number) => `color-mix(in srgb, ${glow} ${percent}%, transparent)`

  return (
    <motion.div
      initial={{ x: -100, opacity: 0, scale: 0.9 }}
      animate={{ x: 0, opacity: 1, scale: 1 }}
      exit={{ x: -100, opacity: 0, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 220, damping: 20 }}
      className="relative"
    >
      <motion.div
        animate={{ scale: [1, 1.15, 1], opacity: [0.35, 0.6, 0.35] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        className="pointer-events-none absolute -inset-3.5 rounded-full blur-sm"
        style={{ background: `radial-gradient(circle, ${tint(30)} 0%, transparent 70%)` }}
      />

      <div
        className="relative flex min-w-28 flex-col items-center justify-center gap-1.5 rounded-[20px] bg-surface/90 px-6 py-4 backdrop-blur-xl"
        style={{ border: `1px solid ${tint(45)}`, boxShadow: `0 0 20px ${tint(40)}` }}
      >
        <span className="text-[10px] font-black tracking-[0.18em] uppercase opacity-80" style={{ color: accent }}>
          {label}
        </span>

        <AnimatePresence mode="wait">
          <motion.div
            key={value}
            initial={{ scale: 1.8, opacity: 0, y: -5 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.6, opacity: 0, y: 5 }}
            transition={{ type: 'spring', stiffness: 350, damping: 18 }}
            className="font-heading text-[2.8rem] leading-[0.95] font-black tracking-tighter italic"
            style={{ color: accent, filter: `drop-shadow(0 0 16px ${glow})` }}
          >
            ×{value}
          </motion.div>
        </AnimatePresence>

        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            filter: [`drop-shadow(0 0 6px ${accent})`, `drop-shadow(0 0 16px ${accent})`, `drop-shadow(0 0 6px ${accent})`],
          }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          className="mt-0.5 flex items-center justify-center"
        >
          <svg width="18" height="22" viewBox="0 0 24 30" fill="none" aria-hidden="true">
            <path
              d="M15 2L3 16H12L9 28L21 14H12L15 2Z"
              fill={`url(#${boltId})`}
              stroke="var(--color-zeus-white)"
              strokeWidth="1.2"
              strokeLinejoin="round"
            />
            <defs>
              <linearGradient id={boltId} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="var(--color-zeus-white)" />
                <stop offset="40%" stopColor={inBonus ? 'var(--color-zeus-lilac-light)' : 'var(--color-zeus-gold-light)'} />
                <stop offset="100%" stopColor={accent} />
              </linearGradient>
            </defs>
          </svg>
        </motion.div>
      </div>
    </motion.div>
  )
}
