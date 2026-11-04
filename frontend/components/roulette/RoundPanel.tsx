import Card from '@/components/ui/Card'
import ProgressBar from '@/components/ui/ProgressBar'
import { BETTING_SECONDS, resultLines } from '@/lib/roulette'
import { formatBalance } from '@/lib/wallet'
import type { PocketColor, RoulettePageLabels, RouletteRound } from '@/types/roulette'

const EYEBROW = 'truncate text-[11px] font-semibold tracking-widest text-muted uppercase'

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
          large ? 'size-14 text-2xl sm:size-16 sm:text-3xl xl:size-21 xl:text-4xl' : 'size-10 text-lg xl:size-14 xl:text-2xl'
        }`}
      >
        {pocket}
      </span>
      <div className="min-w-0">
        <p className={`truncate font-semibold ${large ? 'text-sm xl:text-lg' : 'text-sm xl:text-base'}`}>{first}</p>
        <p className="truncate text-xs text-muted xl:text-[13px]">{second}</p>
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
    <div className="mt-4 border-t border-border pt-4 xl:mt-6 xl:pt-6">
      <p className="mb-2 text-xs text-muted xl:text-[13px]">{labels.last_result}</p>
      <Pocket pocket={last.result} color={last.color} labels={labels} />
    </div>
  )

  if (round.status === 'settled') {
    return (
      <div className="min-w-0 space-y-3 xl:space-y-5">
        <p className={EYEBROW}>{labels.winning_number}</p>
        <Pocket pocket={round.result ?? 0} color={round.color ?? 'green'} labels={labels} large />
        {won && (
          <Card tone="lime" padding="sm" className="xl:p-4">
            <p className="text-xs text-lime">{labels.you_won}</p>
            <p className="truncate font-heading text-xl font-bold text-lime tabular-nums xl:text-3xl">
              +{formatBalance(won.payout)} LC
            </p>
            <p className="truncate text-[11px] text-muted">
              {labels.net_win.replace('{amount}', won.net)} ·{' '}
              {labels.bets_won.replace('{won}', String(won.wonLines)).replace('{total}', String(won.totalLines))}
            </p>
          </Card>
        )}
        <p className="text-xs text-muted xl:text-[15px]">{labels.next_round_in.replace('{seconds}', String(seconds))}</p>
      </div>
    )
  }

  if (round.status === 'spinning') {
    return (
      <div className="min-w-0">
        <p className={EYEBROW}>{labels.no_more_bets}</p>
        <p className="mt-2 truncate font-heading text-2xl leading-tight font-bold xl:text-5xl">{labels.spinning}</p>
        <div className="mt-3 xl:mt-5">
          <ProgressBar value={1} />
        </div>
        <p className="mt-3 text-xs text-muted xl:text-[15px]">{labels.result_in.replace('{seconds}', String(seconds))}</p>
        {lastResult}
      </div>
    )
  }

  return (
    <div className="min-w-0">
      <p className={EYEBROW}>{labels.bets_close_in}</p>
      <p className="mt-1 font-heading text-5xl leading-none font-bold tabular-nums xl:mt-3 xl:text-7xl">{seconds}s</p>
      <div className="mt-4 xl:mt-6">
        <ProgressBar value={seconds / BETTING_SECONDS} />
      </div>
      <p className="mt-3 text-xs text-muted xl:text-[15px]">{labels.place_your_bets}</p>
      {lastResult}
    </div>
  )
}
