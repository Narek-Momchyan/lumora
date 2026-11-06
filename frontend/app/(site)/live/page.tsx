import type { Metadata } from 'next'
import { connection } from 'next/server'
import LiveBoard from '@/components/sports/LiveBoard'
import { getCompetitions, getLiveLabels, getLiveMatches, getSidebarItems } from '@/lib/content'
import { displayLang } from '@/lib/lang'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const items = await getSidebarItems(await displayLang())
  return { title: items?.find((item) => item.url === '/live')?.title }
}

// Live (like the live cards of design 06): every match in play, with its minute and score. The
// page renders the list that is on now; /ws/sports keeps it current. Display only: a live score
// never settles a bet or a prediction.
export default async function LivePage() {
  const lang = await displayLang()
  const [labels, rows, competitions] = await Promise.all([
    getLiveLabels(lang),
    getLiveMatches(lang),
    getCompetitions(lang),
  ])

  return (
    <LiveBoard
      rows={rows ?? []}
      competitions={Object.fromEntries((competitions ?? []).map((item) => [item.code, item.name]))}
      labels={labels}
    />
  )
}
