import { formatBalance } from '@/lib/wallet'
import type { CrashPageLabels, CrashRound, LiveBet } from '@/types/crash'

interface LiveBetsProps {
  bets: LiveBet[]
  round: CrashRound | null
  currency: string
  labels: CrashPageLabels
}

export default function LiveBets({ bets, round, currency, labels }: LiveBetsProps) {
  const crashed = round?.status === 'crashed'

  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-border bg-surface p-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="truncate font-heading text-sm font-semibold">{labels.live_bets}</h2>
        <p className="shrink-0 text-xs text-muted">{labels.players_count.replace('{count}', String(bets.length))}</p>
      </div>

      <ul className="mt-2 max-h-20 min-h-0 flex-1 space-y-1.5 overflow-y-auto [scrollbar-width:none] md:max-h-none [&::-webkit-scrollbar]:hidden">
        {bets.map((bet) => (
          <li key={bet.id} className="grid grid-cols-[minmax(0,1fr)_auto_6.5rem] items-center gap-2 text-xs">
            <p className="flex min-w-0 items-center gap-1.5">
              <span className="truncate">{bet.player}</span>
              {bet.is_bot && (
                <span className="shrink-0 rounded-md bg-surface2 px-1 py-0.5 text-[10px] leading-none text-muted">
                  {labels.bot_badge}
                </span>
              )}
            </p>
            <p className="text-right whitespace-nowrap text-muted tabular-nums">
              {formatBalance(bet.amount)} {currency}
            </p>
            {bet.multiplier ? (
              <p className="flex justify-end gap-1.5 text-right font-semibold whitespace-nowrap text-lime tabular-nums">
                <span>{bet.multiplier}x</span>
                <span className="font-normal">{formatBalance(bet.payout)}</span>
              </p>
            ) : (
              <p className="text-right text-danger">{crashed ? labels.bet_lost : ''}</p>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
