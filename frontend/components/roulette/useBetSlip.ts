'use client'

import { useState } from 'react'
import { spotKey } from '@/lib/roulette'
import type { BetSpot, DraftLine } from '@/types/roulette'

const EMPTY: DraftLine[] = []

// The chips on the board that aren't sent yet. They belong to one round: the next one starts empty.
export default function useBetSlip(roundNumber: number | undefined) {
  const [slip, setSlip] = useState({ round: roundNumber, steps: [EMPTY] })

  const steps = slip.round === roundNumber ? slip.steps : [EMPTY]
  const lines = steps[steps.length - 1]

  function push(next: DraftLine[]) {
    setSlip({ round: roundNumber, steps: [...steps, next] })
  }

  function add(spot: BetSpot, cents: number) {
    const key = spotKey(spot)
    const known = lines.some((line) => spotKey(line) === key)
    push(
      known
        ? lines.map((line) => (spotKey(line) === key ? { ...line, cents: line.cents + cents } : line))
        : [...lines, { ...spot, cents }],
    )
  }

  function undo() {
    if (steps.length > 1) setSlip({ round: roundNumber, steps: steps.slice(0, -1) })
  }

  function clear() {
    setSlip({ round: roundNumber, steps: [EMPTY] })
  }

  function double() {
    push(lines.map((line) => ({ ...line, cents: line.cents * 2 })))
  }

  return { lines, add, undo, clear, double, replace: push }
}
