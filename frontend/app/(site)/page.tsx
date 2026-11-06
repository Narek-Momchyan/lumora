import type { Metadata } from 'next'
import { connection } from 'next/server'
import Card from '@/components/ui/Card'
import BetSlip from '@/components/sports/BetSlip'
import DayChips from '@/components/sports/DayChips'
import FeaturedMatch from '@/components/sports/FeaturedMatch'
import LiveBoard from '@/components/sports/LiveBoard'
import LumoraModelCard from '@/components/sports/LumoraModelCard'
import MatchRow from '@/components/sports/MatchRow'
import PopularPicks from '@/components/sports/PopularPicks'
import PredictionsCard from '@/components/sports/PredictionsCard'
import WatchOdds from '@/components/sports/WatchOdds'
import {
  getBetLabels,
  getCompetitions,
  getMarkets,
  getMatch,
  getLiveLabels,
  getLiveMatches,
  getMatches,
  getPopularPicks,
  getPredictionLabels,
  getSportsPageLabels,
  getSportsUiLabels,
} from '@/lib/content'
import { displayLang } from '@/lib/lang'
import { fill, utcDay } from '@/lib/sports'
import type { Market, Match } from '@/types/sports'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const labels = await getSportsPageLabels(await displayLang())
  return { title: labels.page_title, description: labels.page_description }
}

// The football home (design 06): the nearest match, the matches of a day by league, the bet slip.
export default async function FootballPage({ searchParams }: { searchParams: Promise<{ date?: string }> }) {
  const lang = await displayLang()
  const { date } = await searchParams
  const day = date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : utcDay(0)

  const [ui, bet, competitions, matches, markets, scheduled, openMarkets, live, popular, predict, liveLabels] = await Promise.all([
    getSportsUiLabels(lang),
    getBetLabels(lang),
    getCompetitions(lang),
    getMatches(`date=${day}`, lang),
    getMarkets(`date=${day}&kind=1x2`),
    getMatches('status=scheduled', lang),
    getMarkets('kind=1x2'),
    getLiveMatches(lang),
    getPopularPicks(lang),
    getPredictionLabels(lang),
    getLiveLabels(lang),
  ])

  // The featured match: the nearest scheduled one that has prices (matches come in kickoff order).
  const priced = new Map((openMarkets ?? []).map((market) => [market.match, market]))
  const nearest = (scheduled ?? []).find((match) => priced.has(match.id))
  const featured = nearest ? await getMatch(String(nearest.id), lang) : null
  const featuredMain = nearest ? priced.get(nearest.id) : undefined

  const mainByMatch = new Map<number, Market>((markets ?? []).map((market) => [market.match, market]))
  const byCompetition = new Map<string, Match[]>()
  for (const match of matches ?? [])
    byCompetition.set(match.competition, [...(byCompetition.get(match.competition) ?? []), match])
  const leagues = (competitions ?? []).filter((competition) => byCompetition.has(competition.code))
  const competitionOf = new Map((competitions ?? []).map((competition) => [competition.code, competition]))

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22.5rem]">
      <WatchOdds query={`date=${day}&kind=1x2`} />

      <div className="min-w-0 space-y-6">
        {featured && featuredMain && (
          <FeaturedMatch
            match={featured}
            main={featuredMain}
            competition={competitionOf.get(featured.competition)}
            labels={ui}
            bet={bet}
          />
        )}

        <LiveBoard
          rows={live ?? []}
          competitions={Object.fromEntries((competitions ?? []).map((item) => [item.code, item.name]))}
          labels={liveLabels}
          compact
        />

        <DayChips selected={day} labels={ui} />

        {leagues.length === 0 ? (
          <p className="text-sm text-muted">{ui.no_matches}</p>
        ) : (
          leagues.map((competition) => {
            const rows = byCompetition.get(competition.code)!
            const matchday = rows.find((match) => match.matchday)?.matchday
            return (
              <Card key={competition.id} padding="none" className="overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-3">
                  {competition.flag && (
                    // eslint-disable-next-line @next/next/no-img-element -- a small flag from the admin
                    <img src={competition.flag} alt="" className="size-5 object-contain" />
                  )}
                  <h2 className="font-heading text-sm font-bold">{competition.name}</h2>
                  {matchday && <span className="text-xs text-muted">· {fill(ui.matchday_label, { n: matchday })}</span>}
                  <div className="ml-auto hidden w-64 grid-cols-3 gap-2 pr-16 text-center text-xs text-muted sm:grid">
                    <span>1</span>
                    <span>X</span>
                    <span>2</span>
                  </div>
                </div>
                <ul>
                  {rows.map((match) => (
                    <MatchRow key={match.id} match={match} main={mainByMatch.get(match.id)} labels={ui} />
                  ))}
                </ul>
              </Card>
            )
          })
        )}

        <p className="text-xs text-muted">{ui.odds_note}</p>
      </div>

      <aside className="min-w-0 space-y-6">
        <BetSlip />
        <PopularPicks picks={popular ?? []} labels={ui} bet={bet} />
        <PredictionsCard
          open={(matches ?? []).filter((match) => match.status === 'scheduled').length}
          league={leagues[0]?.code ?? (competitions ?? [])[0]?.code ?? 'PL'}
          labels={predict}
        />
        <LumoraModelCard labels={ui} />
      </aside>
    </div>
  )
}
