'use client'

import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import Link from 'next/link'
import { useState } from 'react'
import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'
import { fill, teamName } from '@/lib/sports'
import type { LiveLabels, LiveMatch } from '@/types/live'
import LiveDot from './LiveDot'
import TeamBadge from './TeamBadge'

interface LiveMatchCardProps {
  item: LiveMatch
  competition: string // the league's name in the page's language
  labels: LiveLabels
}

// A score digit that flips when it changes. With reduced motion it simply changes.
function Digit({ value }: { value: number }) {
  const reduce = useReducedMotion()
  return (
    <span className="relative inline-flex h-7 w-5 justify-center overflow-hidden [perspective:200px]">
      <AnimatePresence initial={false} mode="popLayout">
        <motion.span
          key={value}
          initial={reduce ? false : { rotateX: -90, opacity: 0 }}
          animate={{ rotateX: 0, opacity: 1 }}
          exit={reduce ? { opacity: 0 } : { rotateX: 90, opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="font-heading text-xl leading-7 font-bold tabular-nums"
        >
          {value}
        </motion.span>
      </AnimatePresence>
    </span>
  )
}

// The green "GOAL" burst. It plays once when mounted and ends invisible, so nothing has to remove it.
function GoalBurst({ text }: { text: string }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      aria-live="polite"
      initial={{ opacity: 0, scale: reduce ? 1 : 0.6 }}
      animate={{ opacity: [0, 1, 1, 0], scale: reduce ? 1 : [0.6, 1.15, 1, 1] }}
      transition={{ duration: 3, times: [0, 0.1, 0.8, 1] }}
      className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-2xl bg-lime/15 ring-2 ring-lime"
    >
      <span className="font-heading text-3xl font-extrabold tracking-wider text-lime">{text}</span>
    </motion.div>
  )
}

function statusText(item: LiveMatch, labels: LiveLabels) {
  if (item.status === 'half_time') return labels.half_time
  if (item.status === 'ended') return labels.full_time
  return item.minute === null ? labels.live : fill(labels.minute, { minute: item.minute })
}

// One match in play (design 06's live cards): the red dot, the minute, both clubs and the score. A
// new goal flips the digit and shows GOAL. A score from football-data.org says it is delayed.
export default function LiveMatchCard({ item, competition, labels }: LiveMatchCardProps) {
  const total = item.home_score + item.away_score
  // Adjusting state while rendering: a higher total than we last saw is a goal. The first render is
  // not one, so opening the page in the middle of a match shows no burst.
  const [seen, setSeen] = useState(total)
  const [goals, setGoals] = useState(0)
  if (total !== seen) {
    setSeen(total)
    if (total > seen) setGoals(goals + 1)
  }

  return (
    <Card as="article" padding="md" className="relative overflow-hidden">
      <div className="mb-3 flex min-w-0 items-center gap-2 text-xs">
        <LiveDot />
        <span className="font-semibold whitespace-nowrap text-danger tabular-nums">{statusText(item, labels)}</span>
        <span className="min-w-0 truncate text-muted">{competition}</span>
        {item.delayed && (
          <span className="ml-auto shrink-0" title={labels.delayed_note}>
            <Badge small>{labels.delayed}</Badge>
          </span>
        )}
      </div>

      <Link href={`/matches/${item.match}`} className="block space-y-2 hover:text-accent">
        {[
          { team: item.home, score: item.home_score },
          { team: item.away, score: item.away_score },
        ].map(({ team, score }) => (
          <span key={team.id} className="flex items-center gap-3 text-sm">
            <TeamBadge team={team} size="md" />
            <span className="min-w-0 flex-1 truncate">{teamName(team)}</span>
            <Digit value={score} />
          </span>
        ))}
      </Link>

      {goals > 0 && <GoalBurst key={goals} text={labels.goal} />}
    </Card>
  )
}
