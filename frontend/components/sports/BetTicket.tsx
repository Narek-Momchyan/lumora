import Badge from '@/components/ui/Badge'
import { fill, marketName, pickName, teamName, timeOf } from '@/lib/sports'
import { formatBalance } from '@/lib/wallet'
import type { Bet, BetLabels, BetPickRow, SportsUiLabels } from '@/types/sports'
import Kickoff from './Kickoff'
import TeamBadge from './TeamBadge'

const FRAME = {
  open: 'border-border',
  won: 'border-lime/60',
  lost: 'border-danger/50',
  void: 'border-border',
} as const

const STATUS_TONE = { open: 'muted', won: 'lime', lost: 'danger', void: 'muted' } as const

// A pick's state: ✓ won, ✗ lost, a clock while it waits, a dash when void.
function ResultMark({ result }: { result: BetPickRow['result'] }) {
  const style =
    result === 'won'
      ? 'bg-lime/15 text-lime'
      : result === 'lost'
        ? 'bg-danger/15 text-danger'
        : 'bg-surface2 text-muted'
  const glyph = result === 'won' ? '✓' : result === 'lost' ? '✕' : result === 'void' ? '–' : '◷'
  return (
    <span
      aria-hidden="true"
      className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs ${style}`}
    >
      {glyph}
    </span>
  )
}

interface BetTicketProps {
  bet: Bet
  labels: SportsUiLabels
  names: BetLabels
  currency: string
}

// A bet as a ticket (design 08): its picks with their state, then stake, odds and the win or the return.
export default function BetTicket({ bet, labels, names, currency }: BetTicketProps) {
  const statusLabel = {
    open: names.status_open,
    won: names.status_won,
    lost: names.status_lost,
    void: names.status_void,
  }[bet.status]
  const title = bet.kind === 'express' ? `${names.express} · ${bet.picks.length}` : names.single

  return (
    <article className={`rounded-2xl border bg-surface ${FRAME[bet.status]}`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 pt-4">
        <h3 className="font-heading text-sm font-bold">{title}</h3>
        <span className="text-xs text-muted">
          {fill(labels.ticket_id, { id: bet.id })} · <Kickoff kickoff={bet.created_at} labels={labels} />
        </span>
        <Badge tone={STATUS_TONE[bet.status]} className="ml-auto">
          {statusLabel}
        </Badge>
      </div>

      <ul className="divide-y divide-border px-5 pt-2">
        {bet.picks.map((pick) => (
          <li key={pick.id} className="flex items-center gap-3 py-3">
            <ResultMark result={pick.result} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">
                {pickName(pick.market, pick.line, pick.code, pick.match, names)}
              </p>
              <p className="flex items-center gap-1.5 truncate text-xs text-muted">
                <span className="shrink-0">{marketName(pick.market, names)} ·</span>
                <TeamBadge team={pick.match.home} size="sm" />
                <TeamBadge team={pick.match.away} size="sm" />
                <span className="truncate">
                  {teamName(pick.match.home)} – {teamName(pick.match.away)}
                </span>
              </p>
            </div>
            <div className="shrink-0 text-right">
              {pick.match.status === 'finished' ? (
                <>
                  <p className="text-sm font-bold tabular-nums">
                    {pick.match.home_score} – {pick.match.away_score}
                  </p>
                  <p className="text-[10px] text-muted">{labels.full_time_short}</p>
                </>
              ) : (
                <p className="text-xs text-muted tabular-nums">{timeOf(pick.match.kickoff)}</p>
              )}
            </div>
            <p className="w-12 shrink-0 text-right font-heading text-sm font-bold tabular-nums">{pick.odds}</p>
          </li>
        ))}
      </ul>

      <dl className="mx-5 mt-1 grid grid-cols-3 gap-3 border-t border-dashed border-border py-4">
        <div>
          <dt className="text-xs text-muted">{labels.stake_short}</dt>
          <dd className="font-heading text-lg font-bold tabular-nums">
            {formatBalance(bet.stake)} {currency}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">{labels.odds_label}</dt>
          <dd className="font-heading text-lg font-bold tabular-nums">{bet.total_odds}</dd>
        </div>
        <div className="text-right">
          <dt className="text-xs text-muted">
            {bet.status === 'open' || bet.status === 'lost' ? labels.potential_win : labels.returned}
          </dt>
          <dd
            className={`truncate font-heading text-lg font-bold tabular-nums ${
              bet.status === 'won' ? 'text-lime' : bet.status === 'open' ? 'text-lime' : ''
            } ${bet.status === 'lost' ? 'text-muted line-through' : ''}`}
          >
            {bet.status === 'won' ? '+' : ''}
            {formatBalance(bet.status === 'won' || bet.status === 'void' ? bet.payout : bet.potential_win)} {currency}
          </dd>
        </div>
      </dl>
    </article>
  )
}
