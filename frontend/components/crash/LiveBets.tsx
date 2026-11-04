import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'
import SectionTitle from '@/components/ui/SectionTitle'
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
    <Card padding="md" className="flex min-h-0 flex-1 flex-col">
      <SectionTitle title={labels.live_bets} aside={labels.players_count.replace('{count}', String(bets.length))} />

      <ul className="mt-3 max-h-40 min-h-0 flex-1 space-y-2 overflow-y-auto [scrollbar-width:none] md:max-h-none [&::-webkit-scrollbar]:hidden">
        {bets.map((bet) => (
          <li key={bet.id} className="grid grid-cols-[minmax(0,1fr)_auto_7rem] items-center gap-2 text-[13px] lg:text-sm">
            <p className="flex min-w-0 items-center gap-1.5">
              <span className="truncate">{bet.player}</span>
              {bet.is_bot && (
                <Badge small>{labels.bot_badge}</Badge>
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
    </Card>
  )
}
