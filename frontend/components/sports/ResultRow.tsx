import Link from 'next/link'
import { teamName } from '@/lib/sports'
import type { Match, SportsUiLabels } from '@/types/sports'
import Kickoff from './Kickoff'
import TeamBadge from './TeamBadge'

// A played match of the league's Results tab: the day, both clubs and the final score. A postponed
// or cancelled match shows its status instead of a score. Regular time, like the bets and predictions.
export default function ResultRow({ match, labels }: { match: Match; labels: Pick<SportsUiLabels, 'today' | 'tomorrow'> }) {
  const home = match.home_regular ?? match.home_score
  const away = match.away_regular ?? match.away_score
  const played = home !== null && away !== null

  return (
    <li className="border-t border-border first:border-t-0">
      <Link
        href={`/matches/${match.id}`}
        className="grid grid-cols-[3.5rem_minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-x-3 px-4 py-3 text-sm hover:bg-surface2/50"
      >
        <Kickoff kickoff={match.kickoff} labels={labels} stacked />
        <span className="flex min-w-0 items-center justify-end gap-2">
          <span className="truncate text-right">{teamName(match.home)}</span>
          <TeamBadge team={match.home} size="md" />
        </span>
        <span className="min-w-14 text-center font-heading font-bold tabular-nums">
          {played ? `${home} – ${away}` : '–'}
        </span>
        <span className="flex min-w-0 items-center gap-2">
          <TeamBadge team={match.away} size="md" />
          <span className="truncate">{teamName(match.away)}</span>
        </span>
      </Link>
    </li>
  )
}
