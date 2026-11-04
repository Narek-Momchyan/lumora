import { CHIPS } from '@/lib/roulette'

// Solid colours with a dark ring, so that a chip stands out on red and black numbers alike.
const COLORS: Record<number, string> = {
  1: 'bg-muted text-bg',
  5: 'bg-accent text-bg',
  10: 'bg-accent2 text-text',
  25: 'bg-lime text-bg',
  100: 'bg-danger text-text',
  500: 'bg-text text-bg',
}

function colorFor(value: number) {
  const chip = [...CHIPS].reverse().find((size) => value >= size) ?? CHIPS[0]
  return COLORS[chip]
}

function shortValue(value: number) {
  return value >= 1000 ? `${Number((value / 1000).toFixed(1))}k` : String(value)
}

interface ChipProps {
  value: number
  className?: string
}

export default function Chip({ value, className = '' }: ChipProps) {
  return (
    <span
      className={`flex items-center justify-center rounded-full border-2 border-dashed border-bg/50 font-bold tabular-nums shadow-md ring-2 ring-bg ${colorFor(value)} ${className}`}
    >
      {shortValue(value)}
    </span>
  )
}
