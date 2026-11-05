import Chip from '@/components/ui/Chip'
import { dateOf, utcDay } from '@/lib/sports'
import type { SportsUiLabels } from '@/types/sports'

// Today, Tomorrow and the next two days as filters of the match list (?date=). The note on the
// right says bets close at kickoff.
export default function DayChips({ selected, labels }: { selected: string; labels: SportsUiLabels }) {
  const weekdays = labels.weekdays_short.split(',')
  const days = [0, 1, 2, 3].map((offset) => {
    const day = utcDay(offset)
    const date = new Date(`${day}T12:00:00Z`)
    const name =
      offset === 0
        ? labels.today
        : offset === 1
          ? labels.tomorrow
          : `${weekdays[(date.getUTCDay() + 6) % 7]} ${dateOf(`${day}T12:00:00Z`)}`
    return { day, name, offset }
  })

  return (
    <div className="flex flex-wrap items-center gap-2">
      {days.map(({ day, name, offset }) => (
        <Chip key={day} href={offset === 0 ? '/' : `/?date=${day}`} active={selected === day}>
          {name}
        </Chip>
      ))}
      <p className="ml-auto text-xs text-muted">{labels.bets_close_at_kickoff}</p>
    </div>
  )
}
