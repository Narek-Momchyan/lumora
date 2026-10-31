import { formatBalance, formatDateTime } from '@/lib/wallet'
import { jackpotLabel } from '@/lib/zeus'
import type { SlotSpinRecord, ZeusPageLabels } from '@/types/zeus'

interface SpinHistoryProps {
  spins: SlotSpinRecord[]
  currency: string
  labels: ZeusPageLabels
}

function Fact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className={`truncate text-sm ${mono ? 'font-mono' : ''}`} title={value}>
        {value}
      </dd>
    </div>
  )
}

export default function SpinHistory({ spins, currency, labels }: SpinHistoryProps) {
  const money = (value: string) => `${formatBalance(value)} ${currency}`

  return (
    <section className="rounded-2xl border border-border bg-surface p-4">
      <h2 className="font-heading text-lg font-bold">{labels.history_title}</h2>
      {spins.length === 0 && <p className="mt-2 text-sm text-muted">{labels.history_empty}</p>}

      <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
        {spins.map((spin) => (
          <li key={spin.id} className="rounded-xl bg-surface2 p-3">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 md:grid-cols-6">
              <div className="min-w-0">
                <dt className="text-xs text-muted">{labels.history_time}</dt>
                <dd suppressHydrationWarning className="truncate text-sm">
                  {formatDateTime(spin.created_at)}
                </dd>
              </div>
              <Fact label={labels.history_cost} value={money(spin.cost)} />
              <Fact label={labels.history_win} value={money(spin.payout)} />
              <Fact label={labels.history_client_seed} value={spin.client_seed} mono />
              <Fact label={labels.history_nonce} value={String(spin.nonce)} mono />
              {spin.free_spins_played > 0 && (
                <Fact label={labels.history_free_spins} value={String(spin.free_spins_played)} />
              )}
              <div className="col-span-2 md:col-span-6">
                <Fact label={labels.history_seed_hash} value={spin.server_seed_hash} mono />
              </div>
            </dl>

            {(spin.bonus_buy || spin.jackpot_tier) && (
              <p className="mt-2 text-xs font-semibold text-lime">
                {spin.bonus_buy && labels.history_bonus_buy}
                {spin.bonus_buy && spin.jackpot_tier && ' · '}
                {spin.jackpot_tier &&
                  `${labels.jackpot_won.replace('{tier}', jackpotLabel(spin.jackpot_tier, labels))} ${money(spin.jackpot_win)}`}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
