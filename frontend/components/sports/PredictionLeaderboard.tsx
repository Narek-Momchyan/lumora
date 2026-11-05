'use client'

import { useState } from 'react'
import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'
import Tabs from '@/components/ui/Tabs'
import { fill } from '@/lib/sports'
import type { Leaderboard, LeaderboardRow, PredictionLabels } from '@/types/predictions'

type Scope = 'matchday' | 'season'

interface PredictionLeaderboardProps {
  matchday: Leaderboard
  season: Leaderboard
  matchdayNumber: number
  labels: PredictionLabels
}

function Row({ row, labels, mine }: { row: LeaderboardRow; labels: PredictionLabels; mine: boolean }) {
  return (
    <li
      className={`grid grid-cols-[1.5rem_1.75rem_minmax(0,1fr)_auto_3.75rem] items-center gap-2 rounded-xl px-2 py-2 text-sm ${
        mine ? 'border border-lime/40 bg-lime/5' : ''
      }`}
    >
      <span className={`text-center text-xs font-bold tabular-nums ${row.rank <= 3 ? 'text-lime' : 'text-muted'}`}>
        {row.rank}
      </span>
      <span
        aria-hidden="true"
        className="flex size-7 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent uppercase"
      >
        {row.player.slice(0, 1)}
      </span>
      <span className="flex min-w-0 items-center gap-1.5">
        <span className={`truncate ${mine ? 'text-lime' : ''}`}>{row.player}</span>
        {mine && (
          <Badge small tone="lime">
            {labels.you}
          </Badge>
        )}
      </span>
      <span className="hidden text-xs whitespace-nowrap text-muted min-[400px]:inline">
        {fill(labels.exact_short, { count: row.exact })}
      </span>
      <span className="text-right font-bold whitespace-nowrap tabular-nums">{fill(labels.pts, { points: row.points })}</span>
    </li>
  )
}

// The leaderboard of the league (design 09): the top players of the matchday or the season, and my
// own row with my real rank when I'm not in the top.
export default function PredictionLeaderboard({ matchday, season, matchdayNumber, labels }: PredictionLeaderboardProps) {
  const [scope, setScope] = useState<Scope>('season')
  const board = scope === 'season' ? season : matchday
  const inTop = board.me ? board.rows.some((row) => row.user_id === board.me!.user_id) : false

  return (
    <Card padding="md" className="space-y-4">
      <div className="flex min-w-0 items-baseline justify-between gap-3">
        <h2 className="truncate font-heading text-lg font-bold">{labels.leaderboard}</h2>
        <p className="shrink-0 text-xs text-muted">{fill(labels.players, { count: board.players })}</p>
      </div>

      <Tabs
        label={labels.leaderboard}
        value={scope}
        onChange={setScope}
        tabs={[
          { id: 'matchday', label: fill(labels.tab_matchday, { n: matchdayNumber }) },
          { id: 'season', label: labels.tab_season },
        ]}
      />

      {board.rows.length === 0 ? (
        <p className="text-sm text-muted">{labels.empty_board}</p>
      ) : (
        <ol className="space-y-0.5">
          {board.rows.map((row) => (
            <Row key={row.user_id} row={row} labels={labels} mine={board.me?.user_id === row.user_id} />
          ))}
          {board.me && !inTop && (
            <>
              <li aria-hidden="true" className="py-1 text-center leading-none tracking-widest text-muted">
                ⋯
              </li>
              <Row row={board.me} labels={labels} mine />
            </>
          )}
        </ol>
      )}
    </Card>
  )
}
