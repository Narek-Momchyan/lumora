import type { Metadata } from 'next'
import { connection } from 'next/server'
import PitchHero from '@/components/sports/PitchHero'
import { getSportsPageLabels } from '@/lib/content'
import { displayLang } from '@/lib/lang'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const labels = await getSportsPageLabels(await displayLang())
  return { title: labels.page_title, description: labels.page_description }
}

// The football home (design 06). Until the football data arrives (phase S1), only its hero.
export default async function FootballPage() {
  const labels = await getSportsPageLabels(await displayLang())
  return <PitchHero labels={labels} />
}
