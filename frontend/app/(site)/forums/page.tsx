import type { Metadata } from 'next'
import { connection } from 'next/server'
import ClubCard from '@/components/forums/ClubCard'
import Chip from '@/components/ui/Chip'
import { getCompetitions, getForumLabels, getForums, getSidebarItems } from '@/lib/content'
import { displayLang } from '@/lib/lang'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const items = await getSidebarItems(await displayLang())
  return { title: items?.find((item) => item.url === '/forums')?.title }
}

// Club forums: pick a league, then a club. The league is in the URL (?league=PL) and each chip is a
// real link; an unknown league falls back to the first one instead of breaking the page.
export default async function ForumsPage({ searchParams }: { searchParams: Promise<{ league?: string }> }) {
  const lang = await displayLang()
  const { league: wanted } = await searchParams

  const [labels, competitions] = await Promise.all([getForumLabels(lang), getCompetitions(lang)])
  const leagues = competitions ?? []
  const league = leagues.find((item) => item.code === wanted) ?? leagues[0]
  const clubs = league ? ((await getForums(league.code, lang)) ?? []) : []

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">{labels.page_text}</p>

      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:px-0">
        {leagues.map((item) => (
          <Chip key={item.id} href={`/forums?league=${item.code}`} active={item.code === league?.code}>
            {item.flag && (
              // eslint-disable-next-line @next/next/no-img-element -- a small country flag from the admin
              <img src={item.flag} alt="" className="mr-2 size-4 object-contain" />
            )}
            {item.name}
          </Chip>
        ))}
      </div>

      {clubs.length === 0 ? (
        <p className="text-sm text-muted">{labels.no_clubs}</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {clubs.map((club) => (
            <li key={club.id} className="min-w-0">
              <ClubCard club={club} labels={labels} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
