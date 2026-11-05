'use client'

import { useState } from 'react'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { fill, teamName } from '@/lib/sports'
import type { Prediction, PredictionEntry, PredictionLabels } from '@/types/predictions'
import type { Match } from '@/types/sports'
import ScoreInput from './ScoreInput'

interface PredictScoreCardProps {
  match: Match
  entry: PredictionEntry | null // my prediction state; null when the player is not logged in
  labels: PredictionLabels
}

// "Predict the score" on the match page (design 07): one free prediction for this match, editable
// until kickoff. After kickoff the boxes lock; after full time the points show.
export default function PredictScoreCard({ match, entry, labels }: PredictScoreCardProps) {
  const start = entry?.prediction
  const [home, setHome] = useState(start ? String(start.home_goals) : '')
  const [away, setAway] = useState(start ? String(start.away_goals) : '')
  const [savedAs, setSavedAs] = useState(start ? `${start.home_goals}:${start.away_goals}` : '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const open = entry?.state === 'open'
  const ready = home !== '' && away !== ''
  const dirty = ready && `${Number(home)}:${Number(away)}` !== savedAs
  const outcome = start?.outcome

  async function save() {
    setSaving(true)
    setError('')
    try {
      const row = await apiFetch<Prediction>('/predictions', {
        method: 'POST',
        body: { match: match.id, home_goals: Number(home), away_goals: Number(away) },
      })
      setSavedAs(`${row.home_goals}:${row.away_goals}`)
    } catch (caught) {
      setError(caught instanceof ApiError ? errorDetail(caught, caught.message) : '')
    } finally {
      setSaving(false)
    }
  }

  const badge = {
    exact: [labels.exact_badge, 'lime'],
    result: [labels.result_badge, 'accent'],
    wrong: [labels.wrong_badge, 'muted'],
    void: [labels.void_badge, 'muted'],
  } as const

  return (
    <Card padding="md" className="space-y-4">
      <div className="space-y-1">
        <h2 className="font-heading text-lg font-bold">{labels.predict_title}</h2>
        <p className="text-xs text-muted">{labels.predict_hint}</p>
      </div>

      <div className="flex items-center justify-center gap-3">
        <span className="min-w-0 flex-1 truncate text-right text-sm">{teamName(match.home)}</span>
        <ScoreInput value={home} onChange={setHome} disabled={!open} label={teamName(match.home)} />
        <span className="text-muted" aria-hidden="true">
          :
        </span>
        <ScoreInput value={away} onChange={setAway} disabled={!open} label={teamName(match.away)} />
        <span className="min-w-0 flex-1 truncate text-sm">{teamName(match.away)}</span>
      </div>

      {open ? (
        <Button variant="outline" block disabled={!dirty || saving} onClick={save}>
          {saving ? labels.saving : savedAs && !dirty ? `${labels.saved} ✓` : labels.predict_save}
        </Button>
      ) : (
        <div className="flex flex-wrap items-center justify-center gap-2">
          {entry && outcome && outcome !== 'pending' ? (
            <Badge tone={badge[outcome][1]}>{badge[outcome][0]}</Badge>
          ) : (
            <Badge tone="danger">{labels.locked}</Badge>
          )}
          {match.home_score !== null && match.away_score !== null && entry?.state !== 'open' && (
            <span className="text-xs text-muted">
              {fill(labels.final_score, { score: `${match.home_score} – ${match.away_score}` })}
            </span>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="text-center text-xs text-danger">
          {error}
        </p>
      )}
    </Card>
  )
}
