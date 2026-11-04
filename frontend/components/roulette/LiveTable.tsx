import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'
import SectionTitle from '@/components/ui/SectionTitle'
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
    <Card padding="md" className="flex min-h-0 flex-1 flex-col">
      <SectionTitle title={labels.live_table} aside={labels.players_count.replace('{count}', String(rows.length))} />

      <ul className="mt-3 max-h-48 min-h-0 flex-1 space-y-2 overflow-y-auto [scrollbar-width:none] md:max-h-none [&::-webkit-scrollbar]:hidden">
        {rows.map((row) => (
          <li key={row.seat} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_5rem] items-center gap-2 text-[13px] lg:text-sm">
            <p className="flex min-w-0 items-center gap-1.5">
              <span className={`truncate ${row.seat === mySeat ? 'text-cyan' : ''}`}>{row.player}</span>
              {row.seat === mySeat && (
                <Badge tone="cyan" small>
                  {labels.you_badge}
                </Badge>
              )}
              {row.is_bot && (
                <Badge small>{labels.bot_badge}</Badge>
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
    </Card>
  )
}
