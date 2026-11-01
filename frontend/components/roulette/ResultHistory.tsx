import type { PocketColor, RouletteResult } from '@/types/roulette'

const COLORS: Record<PocketColor, string> = {
  red: 'bg-danger/15 text-danger',
  black: 'bg-surface2 text-text',
  green: 'bg-lime/10 text-lime',
}

interface ResultHistoryProps {
  results: RouletteResult[]
}

export default function ResultHistory({ results }: ResultHistoryProps) {
  return (
    <ul className="flex min-h-7 min-w-0 flex-1 gap-1.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {results.map(({ number, result, color }) => (
        <li
          key={number}
          className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-semibold tabular-nums ${COLORS[color]}`}
        >
          {result}
        </li>
      ))}
    </ul>
  )
}
