'use client'

import { motion } from 'motion/react'
import { useState } from 'react'
import { makeRising } from './effects'

const COINS = 20

interface ParticlesProps {
  currency: string
  scale: number
}

export default function Particles({ currency, scale }: ParticlesProps) {
  const [coins] = useState(() => makeRising(COINS))

  return (
    <div className="pointer-events-none fixed inset-0 z-80 overflow-hidden">
      {coins.map((coin, index) => (
        <motion.div
          key={index}
          initial={{ x: '50vw', y: '100vh', opacity: 1, scale: coin.scale, rotate: 0 }}
          animate={{ x: `${coin.x}vw`, y: '-10vh', rotate: 720, opacity: 0 }}
          transition={{ duration: coin.duration * scale, ease: 'easeOut', delay: coin.delay * scale }}
          className="absolute"
        >
          <svg width="40" height="40" viewBox="0 0 100 100" aria-hidden="true">
            <circle cx="50" cy="50" r="45" fill="var(--color-zeus-yellow)" stroke="var(--color-zeus-coin-edge)" strokeWidth="5" />
            <circle cx="50" cy="50" r="30" fill="none" stroke="var(--color-zeus-coin-edge)" strokeWidth="2" />
            <text x="50" y="63" textAnchor="middle" fill="var(--color-zeus-coin-edge)" fontSize="34" fontWeight="bold">
              {currency}
            </text>
          </svg>
        </motion.div>
      ))}
    </div>
  )
}
