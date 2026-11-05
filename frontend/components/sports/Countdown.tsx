'use client'

import { countdown, secondsUntil } from '@/lib/sports'
import useNow from '@/lib/useNow'

// "05:42:10" until kickoff, ticking every second.
export default function Countdown({ kickoff }: { kickoff: string }) {
  const now = useNow(1000)
  return (
    <span suppressHydrationWarning className="tabular-nums">
      {countdown(secondsUntil(kickoff, now))}
    </span>
  )
}
