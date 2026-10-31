'use client'

import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useRef } from 'react'
import { COLS, ROWS, multiplierColor, teaserColumns } from '@/lib/zeus'
import type { SpeedMode, SymbolDetails } from '@/types/zeus'
import SlotSymbol from './SlotSymbol'

interface SlotGridProps {
  grid: string[][] | null
  gridId: number
  winningCells: [number, number][]
  symbols: SymbolDetails
  speed: SpeedMode
  inBonus: boolean
  teaser: boolean
  onLand: () => void
}

const EMPTY_CELLS = Array.from({ length: ROWS * COLS }, (_, index) => index)
const SPRINGS = {
  normal: { stiffness: 120, damping: 15 },
  turbo: { stiffness: 450, damping: 24 },
  instant: { stiffness: 1000, damping: 40 },
}
const NO_TEASER = { teasing: false, delay: 0 }

function dropDelay(speed: SpeedMode, row: number, col: number, teaserMs: number) {
  if (speed === 'instant') return 0
  if (speed === 'turbo') return col * 0.02 + teaserMs / 1000
  return col * 0.06 + row * 0.04 + teaserMs / 1000
}

export default function SlotGrid({ grid, gridId, winningCells, symbols, speed, inBonus, teaser, onLand }: SlotGridProps) {
  const landed = useRef(false)
  const isWinning = (row: number, col: number) => winningCells.some(([r, c]) => r === row && c === col)
  const columns = teaser && grid ? teaserColumns(grid) : null
  const instant = speed === 'instant'

  useEffect(() => {
    landed.current = false
  }, [gridId])

  function handleLand() {
    if (landed.current) return
    landed.current = true
    onLand()
  }

  return (
    <div
      className={`zeus-grid mx-auto grid aspect-6/5 w-full max-w-[calc((100dvh-25rem)*1.2)] min-w-0 grid-cols-6 grid-rows-5 gap-0.75 p-1.5 sm:gap-1.5 sm:p-2.5 ${
        inBonus ? 'zeus-grid-bonus' : ''
      }`}
    >
      {grid
        ? grid.map((symbolsInRow, row) =>
            symbolsInRow.map((code, col) => {
              const winning = isWinning(row, col)
              const { teasing, delay } = columns?.[col] ?? NO_TEASER

              return (
                // A new grid gets new keys, so every symbol falls again, like in the original game.
                <div
                  key={`${gridId}-${row}-${col}`}
                  className={`zeus-cell ${multiplierColor(code) ? 'zeus-mult-ring' : ''} ${winning ? 'zeus-cell-win' : ''} ${teasing ? 'zeus-teaser' : ''}`}
                  style={{ color: multiplierColor(code) }}
                >
                  <AnimatePresence mode="popLayout">
                    {winning ? (
                      <motion.div
                        key="win-pulse"
                        initial={{ scale: 1, filter: 'brightness(1)' }}
                        animate={{
                          scale: [1, 1.15, 1],
                          filter: ['brightness(1)', 'brightness(1.8)', 'brightness(1)'],
                        }}
                        transition={{ duration: 0.4, repeat: Infinity }}
                        className="relative z-10 h-full w-full"
                      >
                        <SlotSymbol code={code} symbols={symbols} />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="symbol"
                        initial={{ y: -60, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        transition={{
                          type: instant ? 'tween' : 'spring',
                          ...SPRINGS[speed],
                          mass: 0.85,
                          delay: dropDelay(speed, row, col, delay),
                          duration: instant ? 0.05 : undefined,
                        }}
                        onAnimationComplete={handleLand}
                        className="h-full w-full"
                      >
                        <SlotSymbol code={code} symbols={symbols} />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            }),
          )
        : EMPTY_CELLS.map((cell) => <div key={cell} className="zeus-cell" />)}
    </div>
  )
}
