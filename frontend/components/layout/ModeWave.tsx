'use client'

import { motion } from 'motion/react'
import { createPortal } from 'react-dom'
import type { Mode } from '@/lib/mode'

const SWEEP = 0.6 // seconds, as in design/sports-spec.md

interface ModeWaveProps {
  mode: Mode // the section being opened: the wave already has its colours
  x: number // where the switch is, the wave starts there
  y: number
  onDone: () => void
}

// Animation 1 of the spec: a wave in the new section's colours sweeps across the screen from the
// switch while a ball rolls ahead of it, then it fades and leaves the page in its new colours.
export default function ModeWave({ mode, x, y, onDone }: ModeWaveProps) {
  // Only a click creates the wave, so this runs in the browser, never on the server.
  const width = window.innerWidth

  return createPortal(
    // data-theme on the overlay gives it the new section's tokens before <html> finishes fading.
    <div data-theme={mode} aria-hidden="true" className="pointer-events-none fixed inset-0 z-50 overflow-hidden">
      <motion.div
        className="absolute inset-0 bg-linear-to-r from-accent2/70 via-accent/40 to-transparent"
        initial={{ clipPath: `circle(0px at ${x}px ${y}px)`, opacity: 1 }}
        animate={{ clipPath: `circle(${width * 1.6}px at ${x}px ${y}px)`, opacity: [1, 1, 0] }}
        transition={{
          clipPath: { duration: SWEEP, ease: [0.65, 0, 0.35, 1] },
          opacity: { duration: SWEEP + 0.3, times: [0, 0.65, 1] },
        }}
        onAnimationComplete={onDone}
      />
      <motion.span
        className="absolute flex size-7 items-center justify-center rounded-full border-2 border-bg bg-text shadow-lg shadow-accent/40"
        style={{ top: y - 14, left: x - 14 }}
        initial={{ x: 0, rotate: 0, opacity: 1 }}
        animate={{ x: width - x + 40, rotate: 900, opacity: [1, 1, 0] }}
        transition={{ duration: SWEEP, ease: 'easeIn' }}
      >
        <span className="size-2.5 rounded-full bg-bg" />
      </motion.span>
    </div>,
    document.body,
  )
}
