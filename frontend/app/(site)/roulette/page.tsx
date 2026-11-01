import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { connection } from 'next/server'
import RouletteGame from '@/components/roulette/RouletteGame'
import { getGames, getHeaderLabels, getMe, getRouletteBets, getRoulettePageLabels } from '@/lib/content'
import { displayLang } from '@/lib/lang'
import { GAME_SLUG } from '@/lib/roulette'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const labels = await getRoulettePageLabels(await displayLang())
  return { title: labels.page_title, description: labels.page_description }
}

export default async function RoulettePage() {
  const lang = await displayLang()
  const [labels, header, games, me, slips] = await Promise.all([
    getRoulettePageLabels(lang),
    getHeaderLabels(lang),
    getGames(),
    getMe(),
    getRouletteBets(),
  ])

  const game = games?.find(({ slug }) => slug === GAME_SLUG)
  if (!game?.is_playable) notFound()

  return (
    <RouletteGame
      game={game}
      slips={slips ?? []}
      mySeat={`player-${me?.id}`}
      currency={header.currency}
      labels={labels}
    />
  )
}
