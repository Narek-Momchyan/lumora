import Link from 'next/link'
import Badge from '@/components/ui/Badge'
import { fill, teamName } from '@/lib/sports'
import type { BetLabels, Competition, Market, MatchDetail, SportsUiLabels } from '@/types/sports'
import Countdown from './Countdown'
import FormDots from './FormDots'
import Kickoff from './Kickoff'
import OddsCell from './OddsCell'
import ProbabilityBar, { percent } from './ProbabilityBar'
import TeamBadge from './TeamBadge'

interface FeaturedMatchProps {
  match: MatchDetail
  main: Market // its 1X2 market
  competition: Competition | undefined
  labels: SportsUiLabels
  bet: BetLabels
}

// The match to look at first (design 06): the nearest one with prices, its form and the model's view.
export default function FeaturedMatch({ match, main, competition, labels, bet }: FeaturedMatchProps) {
  const [home, draw, away] = ['home', 'draw', 'away'].map((code) => main.selections.find((row) => row.code === code)!)
  const chances = [home, draw, away].map((row) => Number(row.probability))
  const eyebrow = [competition?.name, match.matchday ? fill(labels.matchday_label, { n: match.matchday }) : '']
    .filter(Boolean)
    .join(' · ')
  const picks = [
    { selection: home, label: `1 · ${teamName(match.home)}` },
    { selection: draw, label: `X · ${bet.draw}` },
    { selection: away, label: `2 · ${teamName(match.away)}` },
  ]

  return (
    <section className="relative overflow-hidden rounded-3xl border border-border bg-linear-to-br from-accent2/25 via-surface to-bg p-5 sm:p-6">
      {/* the pitch behind the clubs: the halfway line and the centre circle */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <span className="absolute inset-y-0 left-1/2 border-l border-text/10" />
        <span className="absolute top-1/2 left-1/2 size-40 -translate-1/2 rounded-full border border-text/10 sm:size-52" />
      </div>

      <div className="relative flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-xs font-semibold tracking-widest text-muted uppercase">
          {competition?.flag && (
            // eslint-disable-next-line @next/next/no-img-element -- a small flag from the admin
            <img src={competition.flag} alt="" className="size-4 object-contain" />
          )}
          {eyebrow}
        </p>
        <Badge className="bg-bg/70 text-text">
          <Kickoff kickoff={match.kickoff} labels={labels} /> · {labels.starts_in} <Countdown kickoff={match.kickoff} />
        </Badge>
      </div>

      <div className="relative mt-5 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3 sm:gap-6">
        {[
          { team: match.home, form: match.home_form },
          { team: match.away, form: match.away_form },
        ].map(({ team, form }, index) => (
          <Link
            key={team.id}
            href={`/matches/${match.id}`}
            className={`flex min-w-0 flex-col items-center gap-2 text-center sm:flex-row sm:gap-4 sm:text-left ${
              index === 1 ? 'order-3 sm:flex-row-reverse sm:text-right' : 'order-1'
            }`}
          >
            <TeamBadge team={team} size="xl" />
            <span className="min-w-0">
              <span className="block truncate font-heading text-lg font-bold sm:text-2xl">{team.name}</span>
              <span className="mt-1 block">
                <FormDots form={form} labels={labels} />
              </span>
            </span>
          </Link>
        ))}
        <span className="order-2 font-heading text-sm font-bold tracking-widest text-muted">VS</span>
      </div>

      <div className="relative mt-5 grid grid-cols-1 gap-2 sm:grid-cols-[repeat(3,minmax(0,1fr))_auto]">
        {picks.map(({ selection, label }) => (
          <OddsCell
            key={selection.id}
            selection={selection}
            match={match}
            kind="1x2"
            line={null}
            code={selection.code}
            label={label}
            marketOpen={main.status === 'open'}
          />
        ))}
        <Link
          href={`/matches/${match.id}`}
          className="flex h-11 items-center justify-center rounded-xl border border-dashed border-accent/60 px-4 text-sm font-semibold whitespace-nowrap text-accent hover:bg-accent/10"
        >
          {fill(labels.markets_more, { count: Math.max(0, match.market_count - 1) })} ›
        </Link>
      </div>

      <div className="relative mt-4 flex items-center gap-3 text-xs text-muted">
        <span className="shrink-0">{labels.lumora_model}</span>
        <div className="flex-1">
          <ProbabilityBar home={chances[0]} draw={chances[1]} away={chances[2]} />
        </div>
        <span className="shrink-0 tabular-nums">{chances.map(percent).join(' · ')}</span>
      </div>
    </section>
  )
}
