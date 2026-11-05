'use client'

import { motion, useReducedMotion } from 'motion/react'
import { createPortal } from 'react-dom'

export interface Flight {
  id: number
  x: number // where the odds button was
  y: number
}

// Animation 4 of the spec: the picked odds fly into the bet slip's counter as a small chip.
export default function SlipFlights({ flights, onDone }: { flights: Flight[]; onDone: (id: number) => void }) {
  const reduce = useReducedMotion()
  if (reduce || flights.length === 0) return null

  return createPortal(
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-50">
      {flights.map((flight) => {
        const target = document.querySelector('[data-slip-badge]')?.getBoundingClientRect()
        if (!target) return null
        return (
          <motion.span
            key={flight.id}
            className="absolute size-5 rounded-full bg-lime shadow-lg shadow-lime/40"
            style={{ left: flight.x - 10, top: flight.y - 10 }}
            initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
            animate={{
              x: target.left + target.width / 2 - flight.x,
              y: target.top + target.height / 2 - flight.y,
              scale: 0.5,
              opacity: [1, 1, 0.2],
            }}
            transition={{ duration: 0.45, ease: [0.5, 0, 0.2, 1] }}
            onAnimationComplete={() => onDone(flight.id)}
          />
        )
      })}
    </div>,
    document.body,
  )
}
