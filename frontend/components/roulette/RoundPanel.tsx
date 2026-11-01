import { resultLines } from '@/lib/roulette'
import { formatBalance } from '@/lib/wallet'
import type { PocketColor, RoulettePageLabels, RouletteRound } from '@/types/roulette'

const POCKET_COLORS: Record<PocketColor, string> = {
  red: 'bg-danger text-text',
  black: 'border border-border bg-bg text-text',
  green: 'bg-lime text-bg',
}

interface PocketProps {
  pocket: number
  color: PocketColor
  labels: RoulettePageLabels
  large?: boolean
}

function Pocket({ pocket, color, labels, large = false }: PocketProps) {
  const [first, second] = resultLines(pocket, labels)

  return (
    <div className="flex min-w-0 items-center gap-3">
      <span
        className={`flex shrink-0 items-center justify-center rounded-full font-heading font-bold ${POCKET_COLORS[color]} ${
          large ? 'size-14 text-2xl sm:size-16 sm:text-3xl' : 'size-10 text-lg'
        }`}
      >
        {pocket}
      </span>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold">{first}</p>
        <p className="truncate text-xs text-muted">{second}</p>
      </div>
    </div>
  )
}

interface RoundPanelProps {
  round: RouletteRound | null
  connected: boolean
  seconds: number
  last: { result: number; color: PocketColor } | null
  won: { payout: string; net: string; wonLines: number; totalLines: number } | null
  labels: RoulettePageLabels
}

export default function RoundPanel({ round, connected, seconds, last, won, labels }: RoundPanelProps) {
  if (!connected || !round) {
    return <p className="text-sm text-muted">{labels.connecting}</p>
  }

  const lastResult = last && (
    <div className="mt-3 border-t border-border pt-3">
      <p className="mb-1.5 text-xs text-muted">{labels.last_result}</p>
      <Pocket pocket={last.result} color={last.color} labels={labels} />
    </div>
  )

  if (round.status === 'settled') {
    return (
      <div className="min-w-0 space-y-2">
        <p className="text-[11px] font-semibold tracking-widest text-muted uppercase">{labels.winning_number}</p>
        <Pocket pocket={round.result ?? 0} color={round.color ?? 'green'} labels={labels} large />
        {won && (
          <div className="rounded-xl border border-lime/40 bg-lime/5 p-2.5">
            <p className="text-xs text-lime">{labels.you_won}</p>
            <p className="font-heading text-xl font-bold text-lime tabular-nums">+{formatBalance(won.payout)} LC</p>
            <p className="truncate text-[11px] text-muted">
              {labels.net_win.replace('{amount}', won.net)} ·{' '}
              {labels.bets_won.replace('{won}', String(won.wonLines)).replace('{total}', String(won.totalLines))}
            </p>
          </div>
        )}
        <p className="text-xs text-muted">{labels.next_round_in.replace('{seconds}', String(seconds))}</p>
      </div>
    )
  }

  if (round.status === 'spinning') {
    return (
      <div className="min-w-0">
        <p className="text-[11px] font-semibold tracking-widest text-muted uppercase">{labels.no_more_bets}</p>
        <p className="mt-1 font-heading text-xl leading-tight font-bold sm:text-2xl xl:text-4xl">{labels.spinning}</p>
        <p className="mt-2 text-xs text-muted">{labels.result_in.replace('{seconds}', String(seconds))}</p>
        {lastResult}
      </div>
    )
  }

  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold tracking-widest text-muted uppercase">{labels.bets_close_in}</p>
      <p className="mt-1 font-heading text-4xl font-bold tabular-nums xl:text-5xl">{seconds}s</p>
      <p className="mt-2 text-xs text-muted">{labels.place_your_bets}</p>
      {lastResult}
    </div>
  )
}
