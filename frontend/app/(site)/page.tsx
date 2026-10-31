import type { Metadata } from 'next'
import { connection } from 'next/server'
import BonusBanner from '@/components/lobby/BonusBanner'
import GameFilters from '@/components/lobby/GameFilters'
import GameGrid from '@/components/lobby/GameGrid'
import { getGameCategories, getGames, getLobbyPageLabels, getWallet } from '@/lib/content'
import { displayLang } from '@/lib/lang'
import { isBonusReady } from '@/lib/wallet'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const labels = await getLobbyPageLabels(await displayLang())
  return { title: labels.page_title, description: labels.page_description }
}

export default async function LobbyPage() {
  const lang = await displayLang()
  const [labels, categories, games, wallet] = await Promise.all([
    getLobbyPageLabels(lang),
    getGameCategories(lang),
    getGames(),
    getWallet(),
  ])

  return (
    <div className="space-y-8">
      <BonusBanner wallet={wallet} ready={wallet !== null && isBonusReady(wallet)} labels={labels} />
      <GameFilters games={games ?? []} categories={categories ?? []} labels={labels} />
      <GameGrid games={games ?? []} categories={categories ?? []} labels={labels} />
    </div>
  )
}
