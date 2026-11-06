import Link from 'next/link'
import Badge from '@/components/ui/Badge'
import { authorName, tagLabel } from '@/lib/forums'
import { fill } from '@/lib/sports'
import { formatDateTime } from '@/lib/wallet'
import type { ForumLabels, ForumTopic } from '@/types/forums'

// One topic of a club's forum (design 11): an avatar initial in one accent tint for everyone, the title
// with its tag, pinned and locked marks, who started it, and the counts. Player text (the title and the
// names) is shown only as text, never as HTML. The title opens the topic.
export default function TopicRow({ topic, labels }: { topic: ForumTopic; labels: ForumLabels }) {
  const author = authorName(topic.author.name, labels)

  return (
    <li className="grid grid-cols-[2.25rem_minmax(0,1fr)] items-center gap-x-3 gap-y-1 border-t border-border px-4 py-3 first:border-t-0 sm:grid-cols-[2.25rem_minmax(0,1fr)_4.5rem_4.5rem_9.5rem]">
      <span
        aria-hidden="true"
        className="row-span-2 flex size-9 items-center justify-center rounded-full bg-accent/20 text-sm font-bold text-accent uppercase sm:row-span-1"
      >
        {[...author][0]}
      </span>

      <div className="min-w-0 space-y-1">
        <Link href={`/forums/${topic.forum}/${topic.id}`} className="block truncate text-sm font-semibold hover:text-accent">
          {topic.title}
        </Link>
        <p className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
          {topic.is_pinned && <Badge small tone="lime">{labels.pinned}</Badge>}
          {topic.is_locked && <Badge small tone="danger">{labels.locked}</Badge>}
          <Badge small tone="accent">{tagLabel(topic.tag, labels)}</Badge>
          <span className="min-w-0 truncate">{fill(labels.by_author, { name: author })}</span>
        </p>
      </div>

      <p className="col-start-2 text-xs text-muted sm:hidden">
        {topic.replies} {labels.replies} · {topic.views} {labels.views}
      </p>
      <p className="hidden text-center sm:block">
        <span className="block font-heading text-sm font-bold tabular-nums">{topic.replies}</span>
        <span className="block text-[11px] text-muted">{labels.replies}</span>
      </p>
      <p className="hidden text-center sm:block">
        <span className="block font-heading text-sm font-bold tabular-nums">{topic.views}</span>
        <span className="block text-[11px] text-muted">{labels.views}</span>
      </p>
      <p className="col-start-2 min-w-0 text-xs text-muted sm:col-start-auto sm:text-right">
        <span className="block truncate text-text">{authorName(topic.last_author, labels)}</span>
        <span suppressHydrationWarning className="block truncate tabular-nums">
          {formatDateTime(topic.last_post_at)}
        </span>
      </p>
    </li>
  )
}
