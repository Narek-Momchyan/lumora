import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { connection } from 'next/server'
import BetSlip from '@/components/sports/BetSlip'
import LumoraModelCard from '@/components/sports/LumoraModelCard'
import MarketGrid from '@/components/sports/MarketGrid'
import MatchHero, { Breadcrumb } from '@/components/sports/MatchHero'
import WatchOdds from '@/components/sports/WatchOdds'
import {
  getBetLabels,
  getCompetitions,
  getMarkets,
  getMatch,
  getSportsPageLabels,
  getSportsUiLabels,
} from '@/lib/content'
import { displayLang } from '@/lib/lang'

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  await connection()
  const { id } = await params
  const match = /^\d+$/.test(id) ? await getMatch(id, await displayLang()) : null
  return match ? { title: `${match.home.name} – ${match.away.name}` } : {}
}

// One match (design 07): the head, every market and the bet slip.
export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  if (!/^\d+$/.test(id)) notFound()
  const lang = await displayLang()

  const [match, markets, ui, bet, competitions, page] = await Promise.all([
    getMatch(id, lang),
    getMarkets(`match=${id}`),
    getSportsUiLabels(lang),
    getBetLabels(lang),
    getCompetitions(lang),
    getSportsPageLabels(lang),
  ])
  if (!match) notFound()

  const competition = competitions?.find((item) => item.code === match.competition)
  const main = markets?.find((market) => market.kind === '1x2')

  return (
    <div className="space-y-4">
      <Breadcrumb
        items={[
          { label: page.page_title, href: '/' },
          { label: competition?.name ?? match.competition },
          { label: `${match.home.name} – ${match.away.name}` },
        ]}
      />
      <WatchOdds query={`match=${id}`} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22.5rem]">
        <div className="min-w-0 space-y-6">
          <MatchHero match={match} main={main} competition={competition} labels={ui} bet={bet} />
          {markets && markets.length > 0 ? (
            <MarketGrid match={match} markets={markets} labels={ui} bet={bet} />
          ) : (
            <p className="text-sm text-muted">{ui.no_odds_yet}</p>
          )}
          <p className="text-xs text-muted">{ui.odds_note}</p>
        </div>

        <aside className="min-w-0 space-y-6">
          <BetSlip />
          <LumoraModelCard labels={ui} />
        </aside>
      </div>
    </div>
  )
}
