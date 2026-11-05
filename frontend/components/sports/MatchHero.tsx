import Link from 'next/link'
import Badge from '@/components/ui/Badge'
import { fill, teamName } from '@/lib/sports'
import type { BetLabels, Competition, Market, MatchDetail, SportsUiLabels } from '@/types/sports'
import Countdown from './Countdown'
import FormDots from './FormDots'
import Kickoff from './Kickoff'
import ProbabilityBar, { percent } from './ProbabilityBar'
import TeamBadge from './TeamBadge'

interface MatchHeroProps {
  match: MatchDetail
  main: Market | undefined
  competition: Competition | undefined
  labels: SportsUiLabels
  bet: BetLabels
}

// The head of a match page (design 07): both clubs, their form and table place, the countdown and
// the model's probabilities. After kickoff the countdown gives way to the score.
export default function MatchHero({ match, main, competition, labels, bet }: MatchHeroProps) {
  const chances = main
    ? ['home', 'draw', 'away'].map((code) => Number(main.selections.find((row) => row.code === code)?.probability ?? 0))
    : null
  const started = match.status !== 'scheduled'
  const eyebrow = [competition?.name, match.matchday ? fill(labels.matchday_label, { n: match.matchday }) : '']
    .filter(Boolean)
    .join(' · ')

  const sides = [
    { team: match.home, form: match.home_form, table: match.home_table },
    { team: match.away, form: match.away_form, table: match.away_table },
  ]

  return (
    <section className="relative overflow-hidden rounded-3xl border border-border bg-linear-to-br from-accent2/25 via-surface to-bg p-5 sm:p-7">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <span className="absolute inset-y-0 left-1/2 border-l border-text/10" />
        <span className="absolute top-1/2 left-1/2 size-48 -translate-1/2 rounded-full border border-text/10 sm:size-64" />
        <span className="absolute inset-y-[28%] left-0 w-[12%] border-y border-r border-text/10" />
        <span className="absolute inset-y-[28%] right-0 w-[12%] border-y border-l border-text/10" />
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
          <Kickoff kickoff={match.kickoff} labels={labels} />
        </Badge>
      </div>

      <div className="relative mt-6 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3 sm:gap-6">
        {sides.map(({ team, form, table }, index) => (
          <div
            key={team.id}
            className={`flex min-w-0 flex-col items-center gap-2 text-center ${index === 1 ? 'order-3' : 'order-1'}`}
          >
            <TeamBadge team={team} size="xl" />
            <p className="max-w-full font-heading text-lg leading-tight font-bold break-words sm:text-2xl">{team.name}</p>
            {table && (
              <p className="text-xs text-muted tabular-nums">
                {fill(labels.standing_line, { position: table.position, points: table.points })}
              </p>
            )}
            <FormDots form={form} labels={labels} />
          </div>
        ))}

        <div className="order-2 min-w-0 text-center">
          {started ? (
            <p className="font-heading text-3xl font-bold tabular-nums sm:text-5xl">
              {match.home_score ?? 0} – {match.away_score ?? 0}
            </p>
          ) : (
            <>
              <p className="text-[11px] font-semibold tracking-widest text-muted uppercase">{labels.starts_in}</p>
              <p className="mt-1 font-heading text-2xl font-bold sm:text-4xl">
                <Countdown kickoff={match.kickoff} />
              </p>
              <p className="mt-1 hidden text-xs text-muted sm:block">{labels.bets_close_at_kickoff}</p>
            </>
          )}
        </div>
      </div>

      {chances && (
        <div className="relative mt-6 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted">
            <span>{labels.lumora_model}</span>
            <span>{labels.win_chance}</span>
          </div>
          <ProbabilityBar home={chances[0]} draw={chances[1]} away={chances[2]} />
          <div className="flex justify-between text-xs tabular-nums">
            <span>
              {teamName(match.home)} {percent(chances[0])}
            </span>
            <span>
              {bet.draw} {percent(chances[1])}
            </span>
            <span>
              {teamName(match.away)} {percent(chances[2])}
            </span>
          </div>
        </div>
      )}
    </section>
  )
}

export function Breadcrumb({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav aria-label="breadcrumb" className="flex flex-wrap items-center gap-2 text-xs text-muted">
      {items.map((item, index) => (
        <span key={item.label} className="flex items-center gap-2">
          {index > 0 && <span aria-hidden="true">›</span>}
          {item.href ? (
            <Link href={item.href} className="hover:text-text">
              {item.label}
            </Link>
          ) : (
            <span className="text-text">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
