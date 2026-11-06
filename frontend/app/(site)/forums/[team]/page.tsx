import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { connection } from 'next/server'
import ForumHero from '@/components/forums/ForumHero'
import ForumRules from '@/components/forums/ForumRules'
import NextMatchCard from '@/components/forums/NextMatchCard'
import TopicList from '@/components/forums/TopicList'
import Chip from '@/components/ui/Chip'
import {
  getForum,
  getForumLabels,
  getHeaderLabels,
  getMarkets,
  getMatches,
  getPredictions,
  getSportsUiLabels,
  getTopics,
} from '@/lib/content'
import { SORTS, TAGS, forumHref, sortLabel, tagLabel } from '@/lib/forums'
import { displayLang } from '@/lib/lang'
import { fill, teamName } from '@/lib/sports'
import type { TopicSort } from '@/types/forums'

export async function generateMetadata({ params }: { params: Promise<{ team: string }> }): Promise<Metadata> {
  await connection()
  const { team } = await params
  const lang = await displayLang()
  const club = /^\d+$/.test(team) ? await getForum(team, lang) : null
  if (!club) return {}
  const labels = await getForumLabels(lang)
  return { title: fill(labels.fans, { club: teamName(club.team) }) }
}

// A club's forum (design 11): the head with New topic, the tag chips and the sort, the topics, and on the
// right the club's next match and the rules. The tag and the sort live in the URL as real links; an unknown
// value falls back to "all topics" and "latest". The club id in the URL is the numeric id from /forums.
export default async function ClubForumPage({
  params,
  searchParams,
}: {
  params: Promise<{ team: string }>
  searchParams: Promise<{ tag?: string; sort?: string }>
}) {
  const { team } = await params
  if (!/^\d+$/.test(team)) notFound()
  const query = await searchParams
  const tag = TAGS.find((item) => item === query.tag) ?? ''
  const sort: TopicSort = SORTS.find((item) => item === query.sort) ?? 'latest'
  const lang = await displayLang()

  const [club, labels, header, ui, topics, upcoming] = await Promise.all([
    getForum(team, lang),
    getForumLabels(lang),
    getHeaderLabels(lang),
    getSportsUiLabels(lang),
    getTopics(team, tag, sort),
    getMatches(`team=${team}&status=scheduled`, lang),
  ])
  if (!club) notFound()

  // The club's next match, its 1X2 odds, and whether the player has a prediction for it to attach.
  const next = (upcoming ?? [])[0]
  const [markets, entries] = next
    ? await Promise.all([
        getMarkets(`match=${next.id}&kind=1x2`),
        next.matchday === null ? null : getPredictions(next.competition, next.matchday, lang),
      ])
    : [null, null]
  const mine = entries?.find((entry) => entry.match.id === next?.id)?.prediction
  const predicted =
    next && mine
      ? { id: next.id, home: teamName(next.home), away: teamName(next.away), score: `${mine.home_goals} – ${mine.away_goals}` }
      : null

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22.5rem]">
      <div className="min-w-0 space-y-4">
        <ForumHero club={club} labels={labels} predicted={predicted} serverUnreachable={header.server_unreachable} />

        <div className="flex flex-wrap items-center gap-2">
          <Chip href={forumHref(club.id, '', sort)} active={tag === ''}>
            {labels.all_topics}
          </Chip>
          {TAGS.map((item) => (
            <Chip key={item} href={forumHref(club.id, item, sort)} active={tag === item}>
              {tagLabel(item, labels)}
            </Chip>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm">
          {SORTS.map((item) => (
            <Chip key={item} href={forumHref(club.id, tag, item)} active={sort === item}>
              {sortLabel(item, labels)}
            </Chip>
          ))}
        </div>

        <TopicList
          key={`${tag}|${sort}|${topics?.[0]?.id ?? 0}|${topics?.length ?? 0}|${club.topics}`}
          initial={topics ?? []}
          forum={club.id}
          tag={tag}
          sort={sort}
          labels={labels}
          serverUnreachable={header.server_unreachable}
        />
      </div>

      <aside className="min-w-0 space-y-6">
        {next && <NextMatchCard match={next} main={markets?.[0]} labels={labels} ui={ui} />}
        <ForumRules labels={labels} />
      </aside>
    </div>
  )
}
