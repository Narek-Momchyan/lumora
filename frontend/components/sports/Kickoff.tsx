'use client'

import { dayWord, timeOf } from '@/lib/sports'
import type { SportsUiLabels } from '@/types/sports'

// Kickoff in the visitor's own time zone ("20:30", "Today"). The server renders another zone, so
// the text may differ for a moment: hydration is told to expect it.
export default function Kickoff({
  kickoff,
  labels,
  stacked = false,
}: {
  kickoff: string
  labels: Pick<SportsUiLabels, 'today' | 'tomorrow'>
  stacked?: boolean
}) {
  return (
    <span suppressHydrationWarning className={stacked ? 'flex flex-col leading-tight' : ''}>
      <span className="font-semibold tabular-nums">{timeOf(kickoff)}</span>
      {stacked ? ' ' : ' · '}
      <span className={stacked ? 'text-xs text-muted' : 'text-muted'}>{dayWord(kickoff, labels)}</span>
    </span>
  )
}
