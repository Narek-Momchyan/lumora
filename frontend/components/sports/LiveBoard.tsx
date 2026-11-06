'use client'

import SectionTitle from '@/components/ui/SectionTitle'
import { fromRows, sortedLive } from '@/lib/live'
import { fill } from '@/lib/sports'
import type { LiveLabels, LiveRow } from '@/types/live'
import LiveMatchCard from './LiveMatchCard'
import useLiveMatches from './useLiveMatches'

interface LiveBoardProps {
  rows: LiveRow[] // what is in play when the page was rendered
  competitions: Record<string, string> // league code -> name in the page's language
  labels: LiveLabels
  compact?: boolean // the "Live now" block of the football home: a section title, hidden when nothing is on
}

// The matches in play, live: the page's list at first, then /ws/sports keeps scores, minutes and
// the list itself up to date. Used by /live and by "Live now" on the football home.
export default function LiveBoard({ rows, competitions, labels, compact = false }: LiveBoardProps) {
  const { matches, connected } = useLiveMatches(fromRows(rows))
  const items = sortedLive(matches)

  if (items.length === 0 && compact) return null

  const delayed = items.some((item) => item.delayed)

  return (
    <section className="space-y-3">
      {compact ? (
        <SectionTitle title={labels.live} aside={fill(labels.live_count, { count: items.length })} large />
      ) : (
        <p className="text-sm text-muted">
          {labels.page_text} {items.length > 0 && <b className="text-text">{fill(labels.live_count, { count: items.length })}</b>}
        </p>
      )}

      {!connected && (
        <p role="status" className="text-xs text-muted">
          {labels.reconnecting}
        </p>
      )}

      {items.length === 0 ? (
        <p className="text-sm text-muted">{labels.no_live}</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <li key={item.match}>
              <LiveMatchCard item={item} competition={competitions[item.competition] ?? item.competition} labels={labels} />
            </li>
          ))}
        </ul>
      )}

      {delayed && <p className="text-xs text-muted">{labels.delayed_note}</p>}
    </section>
  )
}
