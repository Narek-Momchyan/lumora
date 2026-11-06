import { notFound } from 'next/navigation'
import AboutTopic from '@/components/forums/AboutTopic'
import NextMatchCard from '@/components/forums/NextMatchCard'
import PostList from '@/components/forums/PostList'
import TopicHeader from '@/components/forums/TopicHeader'
import { Breadcrumb } from '@/components/sports/MatchHero'
import {
  getForum,
  getForumLabels,
  getHeaderLabels,
  getMarkets,
  getMatch,
  getPosts,
  getPredictions,
  getSportsUiLabels,
  getTopic,
} from '@/lib/content'
import { displayLang } from '@/lib/lang'
import { fill, teamName } from '@/lib/sports'

// A topic (design 12): the head, the posts with likes, Reply and Report, the reply box, and on the right
// "About this topic" and the topic's match. Opening it counts the player's view once. A topic that is not
// in the club of the URL is a 404, like a topic that does not exist.
export default async function TopicPage({ params }: { params: Promise<{ team: string; topic: string }> }) {
  const { team, topic: topicId } = await params
  if (!/^\d+$/.test(team) || !/^\d+$/.test(topicId)) notFound()
  const lang = await displayLang()

  const [topic, club, labels, header, ui, posts] = await Promise.all([
    getTopic(topicId, lang),
    getForum(team, lang),
    getForumLabels(lang),
    getHeaderLabels(lang),
    getSportsUiLabels(lang),
    getPosts(topicId, lang),
  ])
  if (!topic || !club || topic.forum !== club.id) notFound()

  // The topic's match, its 1X2 odds, and the player's own prediction for it (to attach to a reply).
  const match = topic.match === null ? null : await getMatch(String(topic.match), lang)
  const [markets, entries] = match
    ? await Promise.all([
        getMarkets(`match=${match.id}&kind=1x2`),
        match.matchday === null ? null : getPredictions(match.competition, match.matchday, lang),
      ])
    : [null, null]
  const mine = entries?.find((entry) => entry.match.id === match?.id)?.prediction
  const predicted =
    match && mine
      ? `${teamName(match.home)} ${mine.home_goals} – ${mine.away_goals} ${teamName(match.away)}`
      : null

  return (
    <div className="space-y-4">
      <Breadcrumb
        items={[
          { label: labels.breadcrumb_forums, href: '/forums' },
          { label: fill(labels.fans, { club: teamName(club.team) }), href: `/forums/${club.id}` },
          { label: topic.title },
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22.5rem]">
        <div className="min-w-0 space-y-4">
          <TopicHeader topic={topic} club={club} labels={labels} />
          <PostList
            topic={topic.id}
            initial={posts ?? []}
            locked={topic.is_locked}
            predicted={predicted}
            labels={labels}
            serverUnreachable={header.server_unreachable}
          />
        </div>

        <aside className="min-w-0 space-y-6">
          <AboutTopic topic={topic} labels={labels} />
          {match && <NextMatchCard match={match} main={markets?.[0]} labels={labels} ui={ui} title={labels.the_match} />}
        </aside>
      </div>
    </div>
  )
}
