'use client'

import { useState } from 'react'
import TeamBadge from '@/components/sports/TeamBadge'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { fill, teamName } from '@/lib/sports'
import type { ForumClub, ForumLabels } from '@/types/forums'
import NewTopicForm, { type PredictedMatch } from './NewTopicForm'

interface ForumHeroProps {
  club: ForumClub
  labels: ForumLabels
  predicted: PredictedMatch | null
  serverUnreachable: string
}

// The head of a club's forum (design 11): crest, "{club} fans", the counts and the New topic button, which
// opens the form right under it. Not shown: members, "online" and Follow (the backend has none of them).
export default function ForumHero({ club, labels, predicted, serverUnreachable }: ForumHeroProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="space-y-4">
      <Card tone="hero" padding="md" className="flex flex-wrap items-center gap-4">
        <TeamBadge team={club.team} size="xl" />
        <div className="min-w-0 flex-1">
          <h2 className="font-heading text-xl leading-tight font-bold break-words sm:text-2xl">{fill(labels.fans, { club: teamName(club.team) })}</h2>
          <p className="truncate text-xs text-muted">
            {fill(labels.topics_count, { count: club.topics })} · {fill(labels.posts_count, { count: club.posts })}
          </p>
        </div>
        {!open && <Button onClick={() => setOpen(true)}>{labels.new_topic}</Button>}
      </Card>

      {open && (
        <NewTopicForm
          forum={club.id}
          labels={labels}
          predicted={predicted}
          serverUnreachable={serverUnreachable}
          onDone={() => setOpen(false)}
        />
      )}
    </div>
  )
}
