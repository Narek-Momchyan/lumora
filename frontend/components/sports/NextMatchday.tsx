import Link from 'next/link'
import Card from '@/components/ui/Card'
import { fill, teamName } from '@/lib/sports'
import type { PredictionLabels } from '@/types/predictions'
import type { Market, Match, SportsUiLabels } from '@/types/sports'
import Kickoff from './Kickoff'
import OddsCell from './OddsCell'
import TeamBadge from './TeamBadge'

interface NextMatchdayProps {
  matchday: number
  matches: Match[]
  markets: Map<number, Market> // the 1X2 market of each match
  labels: PredictionLabels
  ui: SportsUiLabels
}

// The right column of a league page (design 10): the next matchday with its 1 · X · 2 odds, wired
// to the bet slip like the odds of the football home.
export default function NextMatchday({ matchday, matches, markets, labels, ui }: NextMatchdayProps) {
  return (
    <Card padding="md" className="space-y-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="truncate font-heading text-lg font-bold">{fill(labels.next_matchday, { n: matchday })}</h2>
        <p className="shrink-0 text-xs text-muted">1 · X · 2</p>
      </div>

      <ul className="divide-y divide-border">
        {matches.map((match) => {
          const main = markets.get(match.id)
          const prices = main ? ['home', 'draw', 'away'].map((code) => main.selections.find((row) => row.code === code)) : []
          return (
            <li key={match.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 py-3">
              <Link href={`/matches/${match.id}`} className="min-w-0 space-y-1 text-sm hover:text-accent">
                <span className="block text-xs text-muted">
                  <Kickoff kickoff={match.kickoff} labels={ui} />
                </span>
                {[match.home, match.away].map((team) => (
                  <span key={team.id} className="flex items-center gap-2">
                    <TeamBadge team={team} size="sm" />
                    <span className="truncate">{teamName(team)}</span>
                  </span>
                ))}
              </Link>
              {main && prices.every(Boolean) ? (
                <div className="grid w-44 grid-cols-3 gap-1.5">
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
                <p className="text-xs text-muted">{ui.no_odds_yet}</p>
              )}
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
