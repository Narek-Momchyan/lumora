import Link from 'next/link'
import Kickoff from '@/components/sports/Kickoff'
import TeamBadge from '@/components/sports/TeamBadge'
import Card from '@/components/ui/Card'
import { buttonClass } from '@/components/ui/Button'
import { teamName } from '@/lib/sports'
import type { ForumLabels } from '@/types/forums'
import type { Market, Match, SportsUiLabels } from '@/types/sports'

interface NextMatchCardProps {
  match: Match
  main: Market | undefined // the 1X2 market
  labels: ForumLabels
  ui: Pick<SportsUiLabels, 'today' | 'tomorrow'>
  title?: string // "The match" on a topic page; "Next match" by default
}

// The club's next match (design 11): the two clubs, the 1 X 2 odds as the model prices them, and a link to
// the match page, where the bet slip and "predict the score" are. The odds here are only shown.
export default function NextMatchCard({ match, main, labels, ui, title }: NextMatchCardProps) {
  const prices = ['home', 'draw', 'away'].map((code) => main?.selections.find((row) => row.code === code))

  return (
    <Card padding="md" className="space-y-4">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="truncate font-heading text-lg font-bold">{title ?? labels.next_match}</h2>
        <p className="shrink-0 text-xs text-muted">
          <Kickoff kickoff={match.kickoff} labels={ui} />
        </p>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 text-center text-sm">
        {[match.home, match.away].map((team, index) => (
          <div key={team.id} className={`flex min-w-0 flex-col items-center gap-2 ${index === 1 ? 'col-start-3' : ''}`}>
            <TeamBadge team={team} size="lg" />
            <span className="w-full truncate">{teamName(team)}</span>
          </div>
        ))}
        <span className="col-start-2 row-start-1 text-xs font-bold text-muted">VS</span>
      </div>

      {main && prices.every(Boolean) && (
        <dl className="grid grid-cols-3 gap-2 text-center">
          {['1', 'X', '2'].map((name, index) => (
            <div key={name} className="rounded-xl border border-border bg-surface2 px-2 py-2">
              <dt className="text-[11px] text-muted">{name}</dt>
              <dd className="font-heading text-sm font-bold tabular-nums">{prices[index]!.odds}</dd>
            </div>
          ))}
        </dl>
      )}

      <Link href={`/matches/${match.id}`} className={buttonClass({ variant: 'ghost', block: true })}>
        <span className="truncate">{labels.open_match}</span>
      </Link>
    </Card>
  )
}
