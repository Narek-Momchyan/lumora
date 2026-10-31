import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { connection } from 'next/server'
import ZeusGame from '@/components/zeus/ZeusGame'
import {
  getGames,
  getHeaderLabels,
  getJackpotPools,
  getSlotSounds,
  getSlotSpins,
  getSlotSymbolNames,
  getSlotSymbols,
  getWallet,
  getZeusPageLabels,
} from '@/lib/content'
import { displayLang } from '@/lib/lang'
import { GAME_SLUG } from '@/lib/zeus'
import type { SymbolDetails } from '@/types/zeus'
import './zeus.css'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const labels = await getZeusPageLabels(await displayLang())
  return { title: labels.page_title, description: labels.page_description }
}

export default async function ZeusLegacyPage() {
  const lang = await displayLang()
  const [labels, header, games, symbols, names, sounds, pools, spins, wallet] = await Promise.all([
    getZeusPageLabels(lang),
    getHeaderLabels(lang),
    getGames(),
    getSlotSymbols(),
    getSlotSymbolNames(lang),
    getSlotSounds(),
    getJackpotPools(),
    getSlotSpins(),
    getWallet(),
  ])

  const game = games?.find(({ slug }) => slug === GAME_SLUG)
  if (!game?.is_playable) notFound()

  const details: SymbolDetails = {}
  for (const { code, image } of symbols ?? []) {
    details[code] = { image, name: names?.find(({ symbol }) => symbol === code)?.name ?? '' }
  }

  return (
    <ZeusGame
      game={game}
      symbols={details}
      sounds={sounds ?? []}
      pools={pools ?? []}
      spins={spins ?? []}
      balance={wallet?.balance ?? '0.00'}
      header={header}
      labels={labels}
    />
  )
}
