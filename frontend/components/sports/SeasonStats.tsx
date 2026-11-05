import Card from '@/components/ui/Card'
import type { PredictionLabels, PredictionStats } from '@/types/predictions'

// "Your season" (design 09): my points, rank, exact scores and the share of right results in this league.
export default function SeasonStats({
  stats,
  league,
  labels,
}: {
  stats: PredictionStats
  league: string
  labels: PredictionLabels
}) {
  const tiles = [
    { value: String(stats.points), label: labels.points, accent: true },
    { value: stats.rank === null ? '–' : `#${stats.rank}`, label: labels.rank, accent: false },
    { value: String(stats.exact), label: labels.exact_scores, accent: false },
    { value: `${stats.right_percent}%`, label: labels.right_results, accent: false },
  ]

  return (
    <Card padding="md" className="space-y-4">
      <div className="flex min-w-0 items-baseline justify-between gap-3">
        <h2 className="truncate font-heading text-lg font-bold">{labels.your_season}</h2>
        <p className="shrink-0 truncate text-xs text-muted">{league}</p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        {tiles.map(({ value, label, accent }) => (
          <div key={label} className="min-w-0 rounded-xl bg-surface2 p-3">
            <dd className={`truncate font-heading text-2xl font-bold tabular-nums ${accent ? 'text-lime' : ''}`}>
              {value}
            </dd>
            <dt className="truncate text-xs text-muted">{label}</dt>
          </div>
        ))}
      </dl>
    </Card>
  )
}
