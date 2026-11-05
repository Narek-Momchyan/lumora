import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { connection } from 'next/server'
import BetSlip from '@/components/sports/BetSlip'
import LeagueTable from '@/components/sports/LeagueTable'
import MatchRow from '@/components/sports/MatchRow'
import NextMatchday from '@/components/sports/NextMatchday'
import ResultRow from '@/components/sports/ResultRow'
import WatchOdds from '@/components/sports/WatchOdds'
import Card from '@/components/ui/Card'
import Chip from '@/components/ui/Chip'
import {
  getCompetitions,
  getMarkets,
  getMatches,
  getPredictionLabels,
  getSportsUiLabels,
  getStandingZones,
  getStandings,
} from '@/lib/content'
import { displayLang } from '@/lib/lang'
import { fill } from '@/lib/sports'
import type { Market, Match } from '@/types/sports'

const TABS = ['matches', 'table', 'results'] as const
type Tab = (typeof TABS)[number]

export async function generateMetadata({ params }: { params: Promise<{ code: string }> }): Promise<Metadata> {
  await connection()
  const { code } = await params
  const league = (await getCompetitions(await displayLang()))?.find((item) => item.code === code.toUpperCase())
  return league ? { title: league.name } : {}
}

// "2026-08-01" - "2027-05-30" -> "2026/27"
function seasonName(start: string, end: string) {
  return `${start.slice(0, 4)}/${end.slice(2, 4)}`
}

function byMatchday(matches: Match[]) {
  const groups = new Map<number, Match[]>()
  for (const match of matches) {
    const day = match.matchday ?? 0
    groups.set(day, [...(groups.get(day) ?? []), match])
  }
  return groups
}

// One league (design 10): its matches with odds, the table with zones and form, and the results.
// The right column has the bet slip and the next matchday with 1 X 2 odds.
export default async function LeaguePage({
  params,
  searchParams,
}: {
  params: Promise<{ code: string }>
  searchParams: Promise<{ tab?: string }>
}) {
  const code = (await params).code.toUpperCase()
  const wanted = (await searchParams).tab
  const tab: Tab = TABS.includes(wanted as Tab) ? (wanted as Tab) : 'matches'
  const lang = await displayLang()

  const [competitions, labels, ui] = await Promise.all([
    getCompetitions(lang),
    getPredictionLabels(lang),
    getSportsUiLabels(lang),
  ])
  const league = competitions?.find((item) => item.code === code)
  if (!league) notFound()

  const [scheduled, finished, standings, zones] = await Promise.all([
    getMatches(`competition=${code}&status=scheduled`, lang),
    tab === 'results' ? getMatches(`competition=${code}&status=finished`, lang) : null,
    tab === 'table' ? getStandings(code, lang) : null,
    tab === 'table' ? getStandingZones(code) : null,
  ])

  // The next matchday: the lowest one that still has scheduled matches.
  const upcoming = (scheduled ?? []).filter((match) => match.matchday !== null)
  const nextDay = upcoming.length ? Math.min(...upcoming.map((match) => match.matchday!)) : null
  const nextMatches = nextDay === null ? [] : upcoming.filter((match) => match.matchday === nextDay).slice(0, 6)
  // The Matches tab shows the next two matchdays.
  const shownDays = nextDay === null ? [] : [nextDay, nextDay + 1]
  const listed = tab === 'matches' ? upcoming.filter((match) => shownDays.includes(match.matchday!)) : []

  const wantedIds = [...new Set([...nextMatches, ...listed].map((match) => match.id))]
  const markets = wantedIds.length ? await getMarkets(`match=${wantedIds.join(',')}&kind=1x2`) : []
  const mainByMatch = new Map<number, Market>((markets ?? []).map((market) => [market.match, market]))

  const played = Math.max(0, ...(standings ?? []).map((row) => row.played))
  const season = league.season
  const tabLabels: Record<Tab, string> = {
    matches: labels.tab_matches,
    table: labels.tab_table,
    results: labels.tab_results,
  }

  return (
    <div className="space-y-4">
      {wantedIds.length > 0 && <WatchOdds query={`match=${wantedIds.join(',')}&kind=1x2`} />}

      <div className="flex flex-wrap items-center gap-2">
        {TABS.map((id) => (
          <Chip key={id} href={`/leagues/${code}${id === 'matches' ? '' : `?tab=${id}`}`} active={tab === id}>
            {tabLabels[id]}
          </Chip>
        ))}
        {season && (
          <span className="ml-auto text-xs text-muted">
            {tab === 'table' && played > 0
              ? fill(labels.season_after, { season: seasonName(season.start_date, season.end_date), matchday: played })
              : seasonName(season.start_date, season.end_date)}
          </span>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22.5rem]">
        <div className="min-w-0 space-y-4">
          {tab === 'matches' &&
            (listed.length === 0 ? (
              <p className="text-sm text-muted">{labels.no_matches}</p>
            ) : (
              [...byMatchday(listed).entries()].map(([day, rows]) => (
                <Card key={day} padding="none" className="overflow-hidden">
                  <h2 className="px-4 py-3 font-heading text-sm font-bold">{fill(ui.matchday_label, { n: day })}</h2>
                  <ul>
                    {rows.map((match) => (
                      <MatchRow key={match.id} match={match} main={mainByMatch.get(match.id)} labels={ui} />
                    ))}
                  </ul>
                </Card>
              ))
            ))}

          {tab === 'table' &&
            ((standings ?? []).length === 0 ? (
              <p className="text-sm text-muted">{labels.no_results}</p>
            ) : (
              <LeagueTable rows={standings!} zones={zones ?? []} labels={labels} ui={ui} />
            ))}

          {tab === 'results' &&
            ((finished ?? []).length === 0 ? (
              <p className="text-sm text-muted">{labels.no_results}</p>
            ) : (
              [...byMatchday([...finished!].reverse().slice(0, 100)).entries()].map(([day, rows]) => (
                <Card key={day} padding="none" className="overflow-hidden">
                  <h2 className="px-4 py-3 font-heading text-sm font-bold">{fill(ui.matchday_label, { n: day })}</h2>
                  <ul>
                    {rows.map((match) => (
                      <ResultRow key={match.id} match={match} labels={ui} />
                    ))}
                  </ul>
                </Card>
              ))
            ))}
        </div>

        <aside className="min-w-0 space-y-6">
          <BetSlip />
          {nextDay !== null && (
            <NextMatchday matchday={nextDay} matches={nextMatches} markets={mainByMatch} labels={labels} ui={ui} />
          )}
        </aside>
      </div>
    </div>
  )
}
