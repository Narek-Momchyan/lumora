import { GREEN_FROM } from '@/lib/crash'
import type { CrashPoint } from '@/types/crash'

interface CrashHistoryProps {
  points: CrashPoint[]
  title: string
}

export default function CrashHistory({ points, title }: CrashHistoryProps) {
  return (
    // A swipe still reaches the older ones, the scrollbar would only take up room.
    <ul
      aria-label={title}
      className="flex min-h-7 min-w-0 shrink-0 gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      {points.map(({ number, crash_point }) => (
        <li
          key={number}
          className={`shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-semibold tabular-nums ${
            Number(crash_point) >= GREEN_FROM ? 'bg-lime/10 text-lime' : 'bg-danger/15 text-danger'
          }`}
        >
          {crash_point}x
        </li>
      ))}
    </ul>
  )
}
