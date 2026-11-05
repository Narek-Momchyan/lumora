import type { Metadata } from 'next'
import { connection } from 'next/server'
import Chip from '@/components/ui/Chip'
import PredictionLeaderboard from '@/components/sports/PredictionLeaderboard'
import PredictionsBoard from '@/components/sports/PredictionsBoard'
import SeasonStats from '@/components/sports/SeasonStats'
import {
  getCompetitions,
  getLeaderboard,
  getMatchdays,
  getPredictionLabels,
  getPredictionStats,
  getPredictions,
  getSidebarItems,
  getSportsUiLabels,
} from '@/lib/content'
import { displayLang } from '@/lib/lang'
import type { Matchday } from '@/types/predictions'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const items = await getSidebarItems(await displayLang())
  return { title: items?.find((item) => item.url === '/predictions')?.title }
}

// The matchday to open: the one asked for, else the league's current one, else the next with open
// matches, else the last.
function pickMatchday(days: Matchday[], wanted: string | undefined) {
  const asked = days.find((day) => String(day.matchday) === wanted)
  return asked ?? days.find((day) => day.current) ?? days.find((day) => day.open > 0) ?? days.at(-1)
}

// Predictions (design 09): a league's matchday with a score box per match, the leaderboard of the
// league and my season. Free: no LC moves here.
export default async function PredictionsPage({
  searchParams,
}: {
  searchParams: Promise<{ league?: string; matchday?: string }>
}) {
  const lang = await displayLang()
  const params = await searchParams

  const [labels, ui, competitions] = await Promise.all([
    getPredictionLabels(lang),
    getSportsUiLabels(lang),
    getCompetitions(lang),
  ])
  const leagues = competitions ?? []
  const league = leagues.find((item) => item.code === params.league) ?? leagues[0]
  if (!league) return <p className="text-sm text-muted">{labels.no_matches}</p>

  const days = (await getMatchdays(league.code)) ?? []
  const day = pickMatchday(days, params.matchday)
  const [entries, matchdayBoard, seasonBoard, stats] = await Promise.all([
    day ? getPredictions(league.code, day.matchday, lang) : null,
    day ? getLeaderboard(league.code, day.matchday) : null,
    getLeaderboard(league.code),
    getPredictionStats(league.code),
  ])
  const empty = { players: 0, rows: [], me: null }

  const index = day ? days.findIndex((item) => item.matchday === day.matchday) : -1
  const href = (matchday: number) => `/predictions?league=${league.code}&matchday=${matchday}`
  const prev = index > 0 ? href(days[index - 1].matchday) : null
  const next = index >= 0 && index < days.length - 1 ? href(days[index + 1].matchday) : null

  return (
    <div className="space-y-4">
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:px-0">
        {leagues.map((item) => (
          <Chip key={item.id} href={`/predictions?league=${item.code}`} active={item.code === league.code}>
            {item.flag && (
              // eslint-disable-next-line @next/next/no-img-element -- a small flag from the admin
              <img src={item.flag} alt="" className="mr-2 size-4 object-contain" />
            )}
            {item.name}
          </Chip>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22.5rem]">
        <div className="min-w-0">
          {day ? (
            <PredictionsBoard
              key={`${league.code}-${day.matchday}`}
              entries={entries ?? []}
              matchday={day.matchday}
              prevHref={prev}
              nextHref={next}
              labels={labels}
              today={ui}
            />
          ) : (
            <p className="text-sm text-muted">{labels.no_matches}</p>
          )}
        </div>

        <aside className="min-w-0 space-y-6">
          <PredictionLeaderboard
            key={league.code}
            matchday={matchdayBoard ?? empty}
            season={seasonBoard ?? empty}
            matchdayNumber={day?.matchday ?? 0}
            labels={labels}
          />
          {stats && <SeasonStats stats={stats} league={league.name} labels={labels} />}
        </aside>
      </div>
    </div>
  )
}
