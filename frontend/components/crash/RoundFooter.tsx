import type { CrashPageLabels, CrashRound } from '@/types/crash'

interface RoundFooterProps {
  round: CrashRound | null
  rtp: string
  labels: CrashPageLabels
}

export default function RoundFooter({ round, rtp, labels }: RoundFooterProps) {
  const houseEdge = String(Number((100 - Number(rtp)).toFixed(2)))

  return (
    <div className="flex flex-wrap items-center gap-x-3 text-[11px] text-muted sm:text-xs">
      {round && <p>{labels.round_number.replace('{number}', String(round.number))}</p>}

      {round && (
        <details>
          <summary className="cursor-pointer hover:text-text">{labels.provably_fair}</summary>
          {/* Opens over the chart, so the page doesn't grow. */}
          <dl className="absolute inset-x-3 bottom-8 z-10 space-y-2 rounded-xl border border-border bg-surface p-3 break-all shadow-lg">
            <div>
              <dt>{labels.seed_hash_label}</dt>
              <dd className="font-mono text-text">{round.seed_hash}</dd>
            </div>
            {round.seed && (
              <div>
                <dt>{labels.seed_label}</dt>
                <dd className="font-mono text-text">{round.seed}</dd>
              </div>
            )}
          </dl>
        </details>
      )}

      <p>{labels.house_edge.replace('{value}', houseEdge)}</p>
    </div>
  )
}
