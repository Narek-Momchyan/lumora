'use client'

import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { AUTO_CLOSE_MS } from '@/lib/zeus'
import type { ZeusPageLabels } from '@/types/zeus'
import { makeRandomBolts, makeSparks } from './effects'

const BOLTS = 4
const SPARKS = 30

interface BonusTriggerProps {
  count: number
  labels: ZeusPageLabels
  scale: number
  autoClose: boolean
  onClose: () => void
}

export default function BonusTrigger({ count, labels, scale, autoClose, onClose }: BonusTriggerProps) {
  const [bolts] = useState(() => makeRandomBolts(BOLTS))
  const [sparks] = useState(() => makeSparks(SPARKS))
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
      className="fixed inset-0 z-200 flex cursor-pointer items-center justify-center overflow-hidden bg-zeus-night/92 px-4 backdrop-blur-[28px]"
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {bolts.map((bolt, index) => (
          <motion.svg
            key={index}
            viewBox="0 0 1000 1000"
            className="absolute z-5 h-full w-full"
            style={{ filter: 'drop-shadow(0 0 15px var(--color-zeus-gold))' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 0, 0.8, 0] }}
            transition={{ duration: 0.3, repeat: Infinity, repeatDelay: bolt.repeatDelay, delay: index * 0.4 }}
          >
            <path d={bolt.path} fill="none" stroke="var(--color-zeus-white)" strokeWidth="10" strokeLinecap="round" />
          </motion.svg>
        ))}
      </div>

      <motion.div
        animate={{ opacity: [0, 0.4, 0, 0.3, 0] }}
        transition={{ duration: 0.4, repeat: Infinity, repeatDelay: 1 }}
        className="pointer-events-none absolute inset-0 bg-zeus-white mix-blend-overlay"
      />

      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {sparks.map((spark, index) => (
          <motion.div
            key={index}
            initial={{ scale: 0, x: '50vw', y: '50vh', opacity: 1 }}
            animate={{ scale: [0, 1, 0], x: `${spark.x}vw`, y: `${spark.y}vh`, opacity: [1, 0.8, 0] }}
            transition={{ duration: spark.duration, repeat: Infinity, delay: spark.delay }}
            className={`absolute size-1 rounded-full ${spark.gold ? 'bg-zeus-gold text-zeus-gold' : 'bg-zeus-lilac text-zeus-lilac'}`}
            style={{ boxShadow: '0 0 8px currentColor' }}
          />
        ))}
      </div>

      <div className="relative z-1 text-center">
        <motion.h2
          initial={{ scale: 0.4, opacity: 0 }}
          animate={{ scale: [1, 1.08, 1], opacity: 1 }}
          transition={{ duration: 0.5, scale: { duration: 1.5, repeat: Infinity } }}
          className="zeus-gold-text m-0 font-heading text-[clamp(3rem,12vw,6.5rem)] font-black"
          style={{ filter: 'drop-shadow(0 0 40px var(--color-zeus-gold)) drop-shadow(0 0 80px var(--color-zeus-purple))' }}
        >
          {labels.bonus_trigger}
        </motion.h2>

        <motion.div
          initial={{ y: 40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.6 * scale }}
          className="mt-4 font-heading text-[clamp(1.6rem,5vw,2.8rem)] font-black tracking-wide text-zeus-lilac uppercase"
          style={{ filter: 'drop-shadow(0 0 20px var(--color-zeus-purple))' }}
        >
          {labels.free_spins_won.replace('{count}', String(count))}
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: scale }}
          className="mt-3 text-xs tracking-widest text-zeus-lilac/50 uppercase"
        >
          {labels.bonus_blessing}
        </motion.p>

        <motion.button
          type="button"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 2.2 * scale, type: 'spring' }}
          onClick={onClose}
          className="zeus-btn-bonus mt-10 rounded-full px-15 py-4 text-lg"
        >
          {labels.bonus_begin}
        </motion.button>
      </div>
    </motion.div>
  )
}
