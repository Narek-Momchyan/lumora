import { CHIPS } from '@/lib/roulette'

const COLORS: Record<number, string> = {
  1: 'border-muted bg-surface2 text-text',
  5: 'border-cyan bg-cyan/20 text-cyan',
  10: 'border-magenta bg-magenta/30 text-text',
  25: 'border-lime bg-lime/20 text-lime',
  100: 'border-danger bg-danger/30 text-text',
  500: 'border-text bg-text/20 text-text',
}

function colorFor(value: number) {
  const chip = [...CHIPS].reverse().find((size) => value >= size) ?? CHIPS[0]
  return COLORS[chip]
}

interface ChipProps {
  value: number
  className?: string
}

export default function Chip({ value, className = '' }: ChipProps) {
  return (
    <span
      className={`flex items-center justify-center rounded-full border-2 border-dashed font-bold tabular-nums ${colorFor(value)} ${className}`}
    >
      {value}
    </span>
  )
}
