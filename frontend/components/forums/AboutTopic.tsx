import Card from '@/components/ui/Card'
import type { ForumLabels, ForumTopic } from '@/types/forums'

// "About this topic" (design 12): the replies and the views. Views are distinct players, counted when a
// player opens the topic. "Following" is not shown: there is nothing to follow yet.
export default function AboutTopic({ topic, labels }: { topic: ForumTopic; labels: ForumLabels }) {
  const tiles = [
    { value: topic.replies, label: labels.stat_replies },
    { value: topic.views, label: labels.stat_views },
  ]

  return (
    <Card padding="md" className="space-y-4">
      <h2 className="font-heading text-lg font-bold">{labels.about_topic}</h2>
      <dl className="grid grid-cols-2 gap-3">
        {tiles.map(({ value, label }) => (
          <div key={label} className="min-w-0 rounded-xl bg-surface2 p-3">
            <dd className="truncate font-heading text-2xl font-bold tabular-nums">{value}</dd>
            <dt className="truncate text-xs text-muted">{label}</dt>
          </div>
        ))}
      </dl>
    </Card>
  )
}
