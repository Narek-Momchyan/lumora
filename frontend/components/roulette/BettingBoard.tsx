import type { ReactNode } from 'react'
import { colorOf, spotKey, spotLabel } from '@/lib/roulette'
import type { BetSpot, RoulettePageLabels, RouletteRound } from '@/types/roulette'
import Chip from './Chip'

const COLUMNS = Array.from({ length: 12 }, (_, index) => index)
const ROWS = [3, 2, 1] // the board's top row is 3, 6, 9 ...
const CHIP_ON_BOARD = 'pointer-events-none size-7 shrink-0 text-[10px] max-md:-rotate-90'
const CELL_COLORS = { red: 'bg-danger', black: 'bg-surface2', green: 'bg-lime text-bg' }
// Numbers are big as in the design; the words outside them stay smaller, so a translation fits.
const NUMBER_TEXT = 'text-[11px] sm:text-sm lg:text-[15px]'
const WORD_TEXT = 'text-[11px] sm:text-sm'

// On a phone the same board stands upright, so it fits the width. The text turns back.
const UPRIGHT = 'max-md:-rotate-90'

interface BettingBoardProps {
  round: RouletteRound | null
  isOpen: boolean
  amounts: Record<string, number> // cents on each spot
  labels: RoulettePageLabels
  onBet: (spot: BetSpot) => void
}

export default function BettingBoard({ round, isOpen, amounts, labels, onBet }: BettingBoardProps) {
  const settled = round?.status === 'settled'
  const winners = new Set((round?.winning ?? []).map(spotKey))

  function isWinner(spot: BetSpot) {
    if (!settled) return false
    return winners.has(spotKey(spot)) || spotKey(spot) === spotKey({ bet_type: 'straight', value: [round?.result ?? -1] })
  }

  function chip(spot: BetSpot, className = CHIP_ON_BOARD) {
    const cents = amounts[spotKey(spot)]
    return cents ? <Chip value={cents / 100} className={className} /> : null
  }

  // A thin spot on the edge between numbers: a split, street, corner or six line.
  function edge(bet_type: string, value: number[], className: string) {
    const spot = { bet_type, value }
    return (
      <button
        key={spotKey(spot)}
        type="button"
        disabled={!isOpen}
        onClick={() => onBet(spot)}
        aria-label={spotLabel(spot, labels)}
        className={`absolute z-10 flex items-center justify-center rounded-sm hover:enabled:bg-cyan/40 ${className}`}
      >
        {chip(spot)}
      </button>
    )
  }

  function cell(spot: BetSpot, text: ReactNode, className: string) {
    return (
      <button
        type="button"
        disabled={!isOpen}
        onClick={() => onBet(spot)}
        aria-label={spotLabel(spot, labels)}
        className={`relative flex size-full min-h-0 min-w-0 items-center justify-center rounded-md leading-tight font-semibold transition-colors hover:enabled:ring-1 hover:enabled:ring-cyan ${className} ${
          isWinner(spot) ? 'ring-2 ring-cyan' : ''
        }`}
      >
        <span className={UPRIGHT}>{text}</span>
        <span className="absolute inset-0 z-10 flex items-center justify-center">{chip(spot)}</span>
      </button>
    )
  }

  function numberCell(column: number, row: number) {
    const number = column * 3 + row
    const edges = []
    if (column < 11) {
      edges.push(edge('split', [number, number + 3], '-right-1.5 inset-y-1/4 w-3'))
    }
    if (row > 1) {
      edges.push(edge('split', [number - 1, number], 'inset-x-1/4 -bottom-1.5 h-3'))
      if (column < 11) {
        edges.push(edge('corner', [number - 1, number, number + 2, number + 3], '-right-2 -bottom-2 z-20 size-4'))
      }
    } else {
      edges.push(edge('street', [number, number + 1, number + 2], 'inset-x-1/4 -bottom-1.5 h-3'))
      if (column < 11) {
        edges.push(edge('six_line', [number, number + 1, number + 2, number + 3, number + 4, number + 5], '-right-2 -bottom-2 z-20 size-4'))
      }
    }
    if (column === 0) {
      edges.push(edge('split', [0, number], '-left-1.5 inset-y-1/4 w-3'))
      if (row > 1) edges.push(edge('trio', row === 2 ? [0, 1, 2] : [0, 2, 3], '-bottom-2 -left-2 z-20 size-4'))
      else edges.push(edge('first_four', [0, 1, 2, 3], '-bottom-2 -left-2 z-20 size-4'))
    }

    return (
      <div key={number} className="relative min-h-0 min-w-0" style={{ gridColumn: column + 2, gridRow: 4 - row }}>
        {cell({ bet_type: 'straight', value: [number] }, number, `${CELL_COLORS[colorOf(number)]} ${NUMBER_TEXT}`)}
        {edges}
      </div>
    )
  }

  const outside: [BetSpot, string, string][] = [
    [{ bet_type: 'low', value: [] }, labels.bet_low, 'bg-surface2'],
    [{ bet_type: 'even', value: [] }, labels.bet_even, 'bg-surface2'],
    [{ bet_type: 'red', value: [] }, labels.bet_red, 'bg-danger'],
    [{ bet_type: 'black', value: [] }, labels.bet_black, 'bg-surface2'],
    [{ bet_type: 'odd', value: [] }, labels.bet_odd, 'bg-surface2'],
    [{ bet_type: 'high', value: [] }, labels.bet_high, 'bg-surface2'],
  ]
  const dozens: [number, string][] = [
    [1, labels.bet_dozen_1],
    [2, labels.bet_dozen_2],
    [3, labels.bet_dozen_3],
  ]

  return (
    // The upright board is the wide one turned by 90 degrees, so its size comes from the page's width.
    <div className="relative [container-type:inline-size] max-md:aspect-[1/2] md:h-full">
      <div
        className={`grid gap-1 transition-opacity max-md:absolute max-md:top-0 max-md:left-full max-md:h-[100cqw] max-md:w-[200cqw] max-md:origin-top-left max-md:rotate-90 md:size-full ${
          isOpen ? '' : 'opacity-70'
        }`}
        style={{
          gridTemplateColumns: 'minmax(0, 1.15fr) repeat(12, minmax(0, 1fr)) minmax(0, 1.15fr)',
          gridTemplateRows: 'repeat(3, minmax(0, 1fr)) repeat(2, minmax(0, 0.8fr))',
        }}
      >
        <div className="relative min-h-0 min-w-0" style={{ gridColumn: 1, gridRow: '1 / span 3' }}>
          {cell({ bet_type: 'straight', value: [0] }, 0, `${CELL_COLORS.green} ${NUMBER_TEXT}`)}
        </div>

        {COLUMNS.map((column) => ROWS.map((row) => numberCell(column, row)))}

        {ROWS.map((column, index) => (
          <div key={column} className="min-h-0 min-w-0" style={{ gridColumn: 14, gridRow: index + 1 }}>
            {cell({ bet_type: 'column', value: [column] }, labels.bet_column_short, 'bg-surface2 text-[10px] sm:text-xs')}
          </div>
        ))}

        {dozens.map(([dozen, name], index) => (
          <div key={dozen} className="min-h-0 min-w-0" style={{ gridColumn: `${index * 4 + 2} / span 4`, gridRow: 4 }}>
            {cell({ bet_type: 'dozen', value: [dozen] }, name, `bg-surface2 ${WORD_TEXT}`)}
          </div>
        ))}

        {outside.map(([spot, name, color], index) => (
          <div key={spot.bet_type} className="min-h-0 min-w-0" style={{ gridColumn: `${index * 2 + 2} / span 2`, gridRow: 5 }}>
            {cell(spot, name, `${color} ${WORD_TEXT}`)}
          </div>
        ))}
      </div>
    </div>
  )
}
