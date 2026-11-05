'use client'

import { motion, useReducedMotion } from 'motion/react'
import Badge from '@/components/ui/Badge'
import { fill, teamName } from '@/lib/sports'
import type { PredictionEntry, PredictionLabels } from '@/types/predictions'
import type { SportsUiLabels } from '@/types/sports'
import Kickoff from './Kickoff'
import ScoreInput from './ScoreInput'
import TeamBadge from './TeamBadge'

export interface Guess {
  home: string
  away: string
}

interface PredictionRowProps {
  entry: PredictionEntry
  guess: Guess
  onGuess: (guess: Guess) => void
  changed: boolean // typed, not saved yet
  saved: boolean
  labels: PredictionLabels
  today: Pick<SportsUiLabels, 'today' | 'tomorrow'>
}

const OUTCOME_TONE = { exact: 'lime', result: 'accent', wrong: 'muted', void: 'muted' } as const

// A scored prediction's badge pops in (design 09's +3 / +1); a still user sees it at once.
function OutcomeBadge({ entry, labels }: { entry: PredictionEntry; labels: PredictionLabels }) {
  const reduce = useReducedMotion()
  const outcome = entry.prediction?.outcome
  if (!outcome || outcome === 'pending') return null
  const text = { exact: labels.exact_badge, result: labels.result_badge, wrong: labels.wrong_badge, void: labels.void_badge }[
    outcome
  ]
  return (
    <motion.span
      initial={reduce ? false : { scale: 0.5, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 500, damping: 18 }}
      className="inline-flex"
    >
      <Badge tone={OUTCOME_TONE[outcome]}>{text}</Badge>
    </motion.span>
  )
}

// One match of the matchday (design 09): kickoff, the two clubs around the two score boxes, and
// the state on the right: Saved, Locked (with the live score) or +3 / +1 once it is scored.
export default function PredictionRow({ entry, guess, onGuess, changed, saved, labels, today }: PredictionRowProps) {
  const { match, state } = entry
  const open = state === 'open'
  const score = match.home_score !== null && match.away_score !== null ? `${match.home_score} – ${match.away_score}` : null

  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-x-3 gap-y-2 border-t border-border px-4 py-3 first:border-t-0 sm:grid-cols-[4.5rem_minmax(0,1fr)_auto_minmax(0,1fr)_8.5rem]">
      <div className="col-start-1 row-start-1 text-sm">
        <Kickoff kickoff={match.kickoff} labels={today} stacked />
      </div>

      <div className="col-start-1 row-start-2 flex min-w-0 items-center justify-end gap-2 text-sm sm:col-start-2 sm:row-start-1">
        <span className="min-w-0 truncate text-right">{teamName(match.home)}</span>
        <TeamBadge team={match.home} size="md" />
      </div>

      <div className="col-start-2 row-start-2 flex items-center gap-2 sm:col-start-3 sm:row-start-1">
        <ScoreInput
          value={guess.home}
          disabled={!open}
          label={teamName(match.home)}
          onChange={(home) => onGuess({ ...guess, home })}
        />
        <span className="text-muted" aria-hidden="true">
          :
        </span>
        <ScoreInput
          value={guess.away}
          disabled={!open}
          label={teamName(match.away)}
          onChange={(away) => onGuess({ ...guess, away })}
        />
      </div>

      <div className="col-start-3 row-start-2 flex min-w-0 items-center gap-2 text-sm sm:col-start-4 sm:row-start-1">
        <TeamBadge team={match.away} size="md" />
        <span className="min-w-0 truncate">{teamName(match.away)}</span>
      </div>

      <div className="col-start-3 row-start-1 flex flex-col items-end gap-1 text-right sm:col-start-5">
        {open && changed && <span className="text-xs text-muted">{labels.not_saved}</span>}
        {open && !changed && saved && <Badge tone="lime">{labels.saved} ✓</Badge>}
        {state === 'locked' && <Badge tone="danger">{labels.locked}</Badge>}
        {state === 'locked' && score && (
          <span className="text-xs text-muted">{fill(labels.live_score, { score })}</span>
        )}
        {state === 'scored' && <OutcomeBadge entry={entry} labels={labels} />}
        {state === 'scored' && score && (
          <span className="text-xs text-muted">{fill(labels.final_score, { score })}</span>
        )}
      </div>
    </li>
  )
}
