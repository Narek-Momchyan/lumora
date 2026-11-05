import Card from '@/components/ui/Card'
import SectionTitle from '@/components/ui/SectionTitle'
import type { BetSummary, SportsUiLabels } from '@/types/sports'

// "Profit by day": seven bars, green above the line and red below it. A bar's height is its share of
// the biggest day, so a quiet week still reads. Plain divs: no chart library for seven numbers.
export default function ProfitChart({ days, labels }: { days: BetSummary['by_day']; labels: SportsUiLabels }) {
  const weekdays = labels.weekdays_short.split(',')
  const values = days.map((day) => Number(day.profit))
  const biggest = Math.max(1, ...values.map(Math.abs))

  return (
    <Card padding="md" className="space-y-4">
      <SectionTitle title={labels.profit_by_day} aside={labels.profit_by_day_note} />
      <div className="grid grid-cols-7 gap-2" role="img" aria-label={labels.profit_by_day}>
        {days.map((day, index) => {
          const value = values[index]
          const height = Math.max(value === 0 ? 2 : 6, (Math.abs(value) / biggest) * 56)
          const weekday = weekdays[(new Date(`${day.date}T12:00:00Z`).getUTCDay() + 6) % 7]
          return (
            <div key={day.date} className="flex flex-col items-center gap-1">
              <div className="flex h-14 w-full items-end">
                {value >= 0 && (
                  <span
                    className="w-full rounded-md bg-linear-to-t from-accent2 to-lime"
                    style={{ height }}
                    title={`${day.date}: ${day.profit}`}
                  />
                )}
              </div>
              <div className="h-px w-full bg-border" />
              <div className="flex h-14 w-full items-start">
                {value < 0 && (
                  <span
                    className="w-full rounded-md bg-danger"
                    style={{ height }}
                    title={`${day.date}: ${day.profit}`}
                  />
                )}
              </div>
              <span className="text-[10px] text-muted">{weekday}</span>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
