import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { connection } from 'next/server'
import CrashGame from '@/components/crash/CrashGame'
import { getCrashBets, getCrashPageLabels, getGames, getHeaderLabels, getWallet } from '@/lib/content'
import { GAME_SLUG } from '@/lib/crash'
import { displayLang } from '@/lib/lang'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const labels = await getCrashPageLabels(await displayLang())
  return { title: labels.page_title, description: labels.page_description }
}

export default async function CrashPage() {
  const lang = await displayLang()
  const [labels, header, games, wallet, bets] = await Promise.all([
    getCrashPageLabels(lang),
    getHeaderLabels(lang),
    getGames(),
    getWallet(),
    getCrashBets(),
  ])

  const game = games?.find(({ slug }) => slug === GAME_SLUG)
  if (!game?.is_playable) notFound()

  return (
    <CrashGame
      game={game}
      balance={wallet?.balance ?? '0.00'}
      lastBet={bets?.[0] ?? null}
      currency={header.currency}
      labels={labels}
    />
  )
}
