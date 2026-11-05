import Link from 'next/link'
import { teamName } from '@/lib/sports'
import type { Market, Match, SportsUiLabels } from '@/types/sports'
import Kickoff from './Kickoff'
import OddsCell from './OddsCell'
import TeamBadge from './TeamBadge'

interface MatchRowProps {
  match: Match
  main: Market | undefined // the 1X2 market
  labels: SportsUiLabels
}

// One match of the day in the league's list (design 06): time, the two clubs, 1 X 2 and "+N markets".
export default function MatchRow({ match, main, labels }: MatchRowProps) {
  const played = match.status !== 'scheduled'
  const prices = main ? ['home', 'draw', 'away'].map((code) => main.selections.find((row) => row.code === code)) : []
  const more = Math.max(0, match.market_count - 1)

  return (
    <li className="grid grid-cols-[3.5rem_minmax(0,1fr)] items-center gap-x-3 gap-y-2 border-t border-border px-4 py-3 sm:grid-cols-[3.5rem_minmax(0,1fr)_auto]">
      <Kickoff kickoff={match.kickoff} labels={labels} stacked />

      <Link href={`/matches/${match.id}`} className="min-w-0 space-y-1.5 hover:text-accent">
        {[match.home, match.away].map((team, index) => (
          <span key={team.id} className="flex items-center gap-2 text-sm">
            <TeamBadge team={team} size="md" />
            <span className="min-w-0 flex-1 truncate">{team.name}</span>
            {played && (
              <span className="font-heading font-bold tabular-nums">
                {index === 0 ? match.home_score : match.away_score}
              </span>
            )}
          </span>
        ))}
      </Link>

      <div className="col-span-2 flex items-center gap-2 sm:col-span-1">
        {main && prices.every(Boolean) ? (
          <div className="grid flex-1 grid-cols-3 gap-2 sm:w-64 sm:flex-none">
            {prices.map((selection) => (
              <OddsCell
                key={selection!.id}
                selection={selection!}
                match={match}
                kind="1x2"
                line={null}
                code={selection!.code}
                marketOpen={main.status === 'open'}
              />
            ))}
          </div>
        ) : (
          <p className="flex-1 text-xs text-muted">{labels.no_odds_yet}</p>
        )}
        <Link
          href={`/matches/${match.id}`}
          className="w-20 shrink-0 text-right text-xs whitespace-nowrap text-muted hover:text-accent"
          title={teamName(match.home)}
        >
          {more > 0 ? labels.markets_more.replace('{count}', String(more)) : ''}
        </Link>
      </div>
    </li>
  )
}
