'use client'

import { motion } from 'motion/react'
import { COLS, ROWS } from '@/lib/zeus'
import type { SpeedMode, SymbolDetails } from '@/types/zeus'
import SlotSymbol from './SlotSymbol'

interface SlotGridProps {
  grid: string[][] | null
  spinNumber: number
  winningCells: [number, number][]
  symbols: SymbolDetails
  speed: SpeedMode
  inBonus: boolean
}

const EMPTY_CELLS = Array.from({ length: ROWS * COLS }, (_, index) => index)

export default function SlotGrid({ grid, spinNumber, winningCells, symbols, speed, inBonus }: SlotGridProps) {
  const isWinning = (row: number, col: number) => winningCells.some(([r, c]) => r === row && c === col)
  const dropDelay = speed === 'normal' ? 0.05 : 0

  return (
    <div
      className={`mx-auto grid aspect-6/5 w-full max-w-[calc((100dvh-25rem)*1.2)] min-w-0 grid-cols-6 grid-rows-5 gap-1 rounded-2xl border bg-surface p-1 transition-colors sm:gap-1.5 sm:p-2 ${
        inBonus ? 'border-magenta' : 'border-border'
      }`}
    >
      {grid
        ? grid.map((symbolsInRow, row) =>
            symbolsInRow.map((code, col) => (
              <div key={`${row}-${col}`} className="min-h-0 min-w-0 rounded-lg bg-surface2 p-0.5">
                {/* A symbol that stays keeps its key, so only new ones drop in during a tumble. */}
                <motion.div
                  key={`${spinNumber}-${code}`}
                  className="h-full w-full"
                  initial={{ y: speed === 'instant' ? -8 : -40, opacity: 0 }}
                  animate={
                    isWinning(row, col)
                      ? { y: 0, opacity: 1, scale: [1, 1.15, 1], filter: 'brightness(1.6)' }
                      : { y: 0, opacity: 1, scale: 1, filter: 'brightness(1)' }
                  }
                  transition={{
                    duration: speed === 'normal' ? 0.35 : 0.15,
                    delay: col * dropDelay,
                    scale: { duration: 0.4, repeat: isWinning(row, col) ? Infinity : 0 },
                  }}
                >
                  <SlotSymbol code={code} symbols={symbols} />
                </motion.div>
              </div>
            )),
          )
        : EMPTY_CELLS.map((cell) => <div key={cell} className="rounded-lg bg-surface2" />)}
    </div>
  )
}
