'use client'

import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { AUTO_CLOSE_MS } from '@/lib/zeus'
import type { ZeusPageLabels } from '@/types/zeus'
import AnimatedNumber from './AnimatedNumber'
import { makeGoldRain } from './effects'

const RAIN = 60

interface BonusSummaryProps {
  payout: string
  currency: string
  labels: ZeusPageLabels
  scale: number
  autoClose: boolean
  onClose: () => void
}

export default function BonusSummary({ payout, currency, labels, scale, autoClose, onClose }: BonusSummaryProps) {
  const [rain] = useState(() => makeGoldRain(RAIN))
  const close = useRef(onClose)

  useEffect(() => {
    close.current = onClose
  })

  // Waits for a click like the original game, except during autoplay.
  useEffect(() => {
    if (!autoClose) return
    const timer = setTimeout(() => close.current(), AUTO_CLOSE_MS * scale)
    return () => clearTimeout(timer)
  }, [autoClose, scale])

  return (
    <motion.div
      role="status"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-250 flex cursor-pointer items-center justify-center bg-zeus-night/94 backdrop-blur-[28px]"
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {rain.map((drop, index) => (
          <motion.div
            key={index}
            initial={{ y: -20, x: `${drop.x}vw`, opacity: 1, rotate: 0 }}
            animate={{ y: '108vh', rotate: drop.rotate, opacity: [1, 1, 0] }}
            transition={{ duration: drop.duration, repeat: Infinity, delay: drop.delay, ease: 'linear' }}
            className={`absolute size-1.25 ${drop.round ? 'rounded-full' : 'rounded-[1px]'} ${drop.gold ? 'bg-zeus-gold text-zeus-gold' : 'bg-zeus-lilac text-zeus-lilac'}`}
            style={{ boxShadow: '0 0 4px currentColor' }}
          />
        ))}
      </div>

      <motion.div
        initial={{ scale: 0.75, y: 60 }}
        animate={{ scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 180, damping: 22 }}
        className="zeus-glass relative w-[92%] max-w-130 overflow-hidden border border-zeus-purple/35 px-8 py-12 text-center shadow-[0_0_80px_var(--color-zeus-plum)]"
      >
        <motion.h2
          animate={{ scale: [1, 1.02, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="mb-3 font-heading text-[clamp(1.4rem,4.2vw,2.2rem)] leading-tight font-black wrap-break-word text-zeus-lilac"
          style={{ filter: 'drop-shadow(0 0 20px var(--color-zeus-purple))' }}
        >
          {labels.congratulations}
        </motion.h2>

        <p className="mb-8 text-xs tracking-widest text-zeus-lilac/50 uppercase">{labels.bonus_complete}</p>
        <p className="mb-2 text-xs tracking-widest text-muted uppercase">{labels.total_win}</p>

        <div className="zeus-gold-text mb-10 font-heading text-[clamp(2.5rem,11vw,5rem)] leading-[1.05] font-black">
          <AnimatedNumber value={Number(payout)} from={0} /> {currency}
        </div>

        <button type="button" onClick={onClose} className="zeus-btn-bonus rounded-full px-16 py-4 text-base">
          {labels.collect}
        </button>
      </motion.div>
    </motion.div>
  )
}
