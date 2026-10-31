'use client'

import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { makeBolt } from './effects'

interface LightningBoltProps {
  active: boolean
  scale: number
}

// Mounted for one strike only, so every strike draws a new shape.
function Strike({ scale }: { scale: number }) {
  const [bolt] = useState(makeBolt)

  return (
    <div className="pointer-events-none fixed inset-0 z-100 flex items-center justify-center overflow-hidden">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 1, 0.4, 0.8, 0] }}
        transition={{ duration: 0.4 * scale, times: [0, 0.1, 0.3, 0.5, 1] }}
        className="fixed inset-0 z-1 bg-zeus-white"
      />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.6, 0] }}
        transition={{ duration: 0.8 * scale }}
        className="fixed inset-0 z-2"
        style={{
          background:
            'radial-gradient(circle, color-mix(in srgb, var(--color-zeus-ice) 40%, transparent) 0%, color-mix(in srgb, var(--color-zeus-purple) 30%, transparent) 100%)',
        }}
      />

      <svg
        viewBox="0 0 1000 1000"
        className="absolute z-3 h-full w-full"
        style={{ filter: 'drop-shadow(0 0 20px var(--color-zeus-ice)) drop-shadow(0 0 40px var(--color-zeus-purple))' }}
      >
        <motion.path
          d={bolt.path}
          fill="none"
          stroke="var(--color-zeus-white)"
          strokeWidth="12"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: [0, 1, 0.8, 1, 0] }}
          transition={{ duration: 0.4 * scale, ease: 'easeOut' }}
        />

        <motion.path
          d={bolt.path}
          fill="none"
          stroke="var(--color-zeus-ice)"
          strokeWidth="25"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: [0, 0.7, 0] }}
          transition={{ duration: 0.6 * scale, ease: 'easeOut' }}
          style={{ filter: 'blur(8px)' }}
        />

        {bolt.branches.map((path, index) => (
          <motion.path
            key={path}
            d={path}
            fill="none"
            stroke="var(--color-zeus-purple)"
            strokeWidth="4"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 0] }}
            transition={{ duration: 0.3 * scale, delay: 0.1 * index * scale }}
          />
        ))}
      </svg>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.3, 0] }}
        transition={{ duration: 0.2 * scale, delay: 0.1 * scale }}
        className="fixed inset-0 z-4 bg-zeus-ice mix-blend-overlay"
      />
    </div>
  )
}

export default function LightningBolt({ active, scale }: LightningBoltProps) {
  return <AnimatePresence>{active && <Strike scale={scale} />}</AnimatePresence>
}
