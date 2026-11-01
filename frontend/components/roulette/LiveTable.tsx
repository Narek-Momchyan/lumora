import { spotLabel } from '@/lib/roulette'
import { formatBalance, fromCents, toCents } from '@/lib/wallet'
import type { RoulettePageLabels, RouletteRound, SeatPayout, TableBet, TableLine } from '@/types/roulette'

interface Seat {
  seat: string
  player: string
  is_bot: boolean
  cents: number
  payoutCents: number
  lines: TableLine[]
}

// A player's slips are one row. `payouts` comes with the settlement, a snapshot has it in `bets`.
function seatRows(bets: TableBet[], payouts: SeatPayout[]) {
  const seats = new Map<string, Seat>()
  for (const bet of bets) {
    const seat = seats.get(bet.seat) ?? { ...bet, cents: 0, payoutCents: 0, lines: [] }
    seat.cents += toCents(bet.amount)
    seat.payoutCents += toCents(bet.payout)
    seat.lines = [...seat.lines, ...bet.lines]
    seats.set(bet.seat, seat)
  }
  for (const { seat, payout } of payouts) {
    const row = seats.get(seat)
    if (row) row.payoutCents = toCents(payout)
  }
  return [...seats.values()]
}

interface LiveTableProps {
  bets: TableBet[]
  payouts: SeatPayout[]
  round: RouletteRound | null
  mySeat: string
  currency: string
  labels: RoulettePageLabels
}

export default function LiveTable({ bets, payouts, round, mySeat, currency, labels }: LiveTableProps) {
  const settled = round?.status === 'settled'
  const rows = seatRows(bets, payouts).sort((a, b) => Number(b.seat === mySeat) - Number(a.seat === mySeat))

  function summary({ lines }: Seat) {
    if (lines.length === 1) return spotLabel(lines[0], labels)
    return labels.bets_count.replace('{count}', String(lines.length))
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-border bg-surface p-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="truncate font-heading text-sm font-semibold">{labels.live_table}</h2>
        <p className="shrink-0 text-xs text-muted">{labels.players_count.replace('{count}', String(rows.length))}</p>
      </div>

      <ul className="mt-2 max-h-40 min-h-0 flex-1 space-y-1.5 overflow-y-auto [scrollbar-width:none] md:max-h-none [&::-webkit-scrollbar]:hidden">
        {rows.map((row) => (
          <li key={row.seat} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_4.5rem] items-center gap-2 text-xs">
            <p className="flex min-w-0 items-center gap-1.5">
              <span className={`truncate ${row.seat === mySeat ? 'text-cyan' : ''}`}>{row.player}</span>
              {row.seat === mySeat && (
                <span className="shrink-0 rounded-md bg-cyan/10 px-1 py-0.5 text-[10px] leading-none text-cyan">
                  {labels.you_badge}
                </span>
              )}
              {row.is_bot && (
                <span className="shrink-0 rounded-md bg-surface2 px-1 py-0.5 text-[10px] leading-none text-muted">
                  {labels.bot_badge}
                </span>
              )}
            </p>
            <p className="truncate text-muted">{summary(row)}</p>
            <p className={`text-right whitespace-nowrap tabular-nums ${settled && row.payoutCents ? 'font-semibold text-lime' : 'text-muted'}`}>
              {settled && row.payoutCents
                ? `+${formatBalance(fromCents(row.payoutCents))}`
                : `${formatBalance(fromCents(row.cents))} ${currency}`}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
