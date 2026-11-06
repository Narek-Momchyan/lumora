import Link from 'next/link'
import TeamBadge from '@/components/sports/TeamBadge'
import { cardClass } from '@/components/ui/Card'
import { fill } from '@/lib/sports'
import type { ForumClub, ForumLabels } from '@/types/forums'

// One club's forum in the list: its crest, its name and how much is going on. The link is the club's
// numeric id, the same in every forum page (/forums/<id>).
export default function ClubCard({ club, labels }: { club: ForumClub; labels: ForumLabels }) {
  const name = club.team.short_name || club.team.name

  return (
    <Link
      href={`/forums/${club.id}`}
      className={`${cardClass({ padding: 'md' })} flex min-w-0 items-center gap-3 transition-colors hover:border-accent/60`}
    >
      <TeamBadge team={club.team} size="lg" />
      <span className="min-w-0">
        <span className="block truncate font-heading text-sm font-bold">{name}</span>
        <span className="block truncate text-xs text-muted">
          {fill(labels.topics_count, { count: club.topics })} · {fill(labels.posts_count, { count: club.posts })}
        </span>
      </span>
    </Link>
  )
}
