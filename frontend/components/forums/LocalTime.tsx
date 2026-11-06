'use client'

import { formatDateTime } from '@/lib/wallet'

// A moment in the visitor's own time zone, digits only. The server renders another zone, so the text may
// differ for a moment: hydration is told to expect it (the same as the kickoff time).
export default function LocalTime({ value, className = '' }: { value: string; className?: string }) {
  return (
    <span suppressHydrationWarning className={`tabular-nums ${className}`}>
      {formatDateTime(value)}
    </span>
  )
}
