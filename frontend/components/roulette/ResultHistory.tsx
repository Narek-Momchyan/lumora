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
    <ul className="flex min-h-7 min-w-0 shrink-0 gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {results.map(({ number, result, color }) => (
        <li
          key={number}
          className={`flex h-7 min-w-9 shrink-0 items-center justify-center rounded-lg px-2 text-xs font-semibold tabular-nums ${COLORS[color]}`}
        >
          {result}
        </li>
      ))}
    </ul>
  )
}
