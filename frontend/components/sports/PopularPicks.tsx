import Card from '@/components/ui/Card'
import SectionTitle from '@/components/ui/SectionTitle'
import { marketName, pickName, teamName } from '@/lib/sports'
import type { BetLabels, PopularPick, SportsUiLabels } from '@/types/sports'
import Kickoff from './Kickoff'
import OddsCell from './OddsCell'

// "Popular right now": the open picks the most bets contain. Nothing is shown until players bet.
export default function PopularPicks({
  picks,
  labels,
  bet,
}: {
  picks: PopularPick[]
  labels: SportsUiLabels
  bet: BetLabels
}) {
  if (picks.length === 0) return null

  return (
    <Card padding="md" className="space-y-1">
      <SectionTitle title={labels.popular_title} />
      <ul className="divide-y divide-border">
        {picks.map((pick) => (
          <li key={pick.id} className="flex items-center gap-3 py-3">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">
                {pickName(pick.market, pick.line, pick.code, pick.match, bet)}
              </p>
              <p className="truncate text-xs text-muted">
                {marketName(pick.market, bet)} · {teamName(pick.match.home)} – {teamName(pick.match.away)} ·{' '}
                <Kickoff kickoff={pick.match.kickoff} labels={labels} />
              </p>
            </div>
            <div className="w-20 shrink-0">
              <OddsCell selection={pick} match={pick.match} kind={pick.market} line={pick.line} code={pick.code} />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}
