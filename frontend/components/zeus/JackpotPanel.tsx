import { formatBalance } from '@/lib/wallet'
import { jackpotLabel } from '@/lib/zeus'
import type { ZeusPageLabels } from '@/types/zeus'

const TIERS = ['GRAND', 'MAJOR', 'MINOR', 'MINI']

interface JackpotPanelProps {
  pools: Record<string, string>
  currency: string
  labels: ZeusPageLabels
}

export default function JackpotPanel({ pools, currency, labels }: JackpotPanelProps) {
  return (
    <section aria-label={labels.jackpots_label} className="grid grid-cols-4 gap-1 sm:gap-2">
      {TIERS.map((tier) => (
        <div key={tier} className="min-w-0 rounded-xl border border-border bg-surface px-1 py-1.5 text-center sm:px-3 sm:py-2">
          <p className="truncate text-[10px] font-semibold text-muted sm:text-xs">{jackpotLabel(tier, labels)}</p>
          <p className="truncate font-heading text-[11px] font-bold text-cyan sm:text-base">
            {pools[tier] ? formatBalance(pools[tier]) : ''}
            <span className="hidden sm:inline"> {currency}</span>
          </p>
        </div>
      ))}
    </section>
  )
}
