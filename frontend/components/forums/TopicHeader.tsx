import TeamBadge from '@/components/sports/TeamBadge'
import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'
import { authorName, tagLabel } from '@/lib/forums'
import { fill } from '@/lib/sports'
import type { ForumClub, ForumLabels, ForumTopic } from '@/types/forums'
import LocalTime from './LocalTime'

// The head of a topic (design 12): the club's crest, the title, its marks, who started it and when, and the
// counts. The title and the name are player text, shown only as text.
export default function TopicHeader({ topic, club, labels }: { topic: ForumTopic; club: ForumClub; labels: ForumLabels }) {
  return (
    <Card padding="md" className="flex items-start gap-4">
      <TeamBadge team={club.team} size="lg" />
      <div className="min-w-0 flex-1 space-y-2">
        <h2 className="font-heading text-xl leading-tight font-bold break-words sm:text-2xl">{topic.title}</h2>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
          {topic.is_pinned && <Badge small tone="lime">{labels.pinned}</Badge>}
          {topic.is_locked && <Badge small tone="danger">{labels.locked}</Badge>}
          <Badge small tone="accent">{tagLabel(topic.tag, labels)}</Badge>
          <span>{fill(labels.by_author, { name: authorName(topic.author.name, labels) })}</span>
          <LocalTime value={topic.created_at} />
          <span>
            · {topic.replies} {labels.replies} · {topic.views} {labels.views}
          </span>
        </p>
      </div>
    </Card>
  )
}
