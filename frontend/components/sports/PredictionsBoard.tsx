'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import ProgressBar from '@/components/ui/ProgressBar'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { fill } from '@/lib/sports'
import type { Prediction, PredictionEntry, PredictionLabels } from '@/types/predictions'
import type { SportsUiLabels } from '@/types/sports'
import PredictionRow, { type Guess } from './PredictionRow'

interface PredictionsBoardProps {
  entries: PredictionEntry[]
  matchday: number
  prevHref: string | null
  nextHref: string | null
  labels: PredictionLabels
  today: Pick<SportsUiLabels, 'today' | 'tomorrow'>
}

type Guesses = Record<number, Guess>

function initial(entries: PredictionEntry[]) {
  const guesses: Guesses = {}
  for (const { match, prediction } of entries) {
    guesses[match.id] = prediction
      ? { home: String(prediction.home_goals), away: String(prediction.away_goals) }
      : { home: '', away: '' }
  }
  return guesses
}

const filled = (guess: Guess) => guess.home !== '' && guess.away !== ''
const same = (a: Guess, b: Guess) => a.home === b.home && a.away === b.away

// The matchday's board (design 09): matchday arrows, the progress, every match with its two boxes
// and the "Save predictions" bar. Nothing is saved until the button: one request saves all
// changed matches, or none of them.
export default function PredictionsBoard({ entries, matchday, prevHref, nextHref, labels, today }: PredictionsBoardProps) {
  const router = useRouter()
  const [saved, setSaved] = useState<Guesses>(() => initial(entries)) // what the server has
  const [guesses, setGuesses] = useState<Guesses>(() => initial(entries))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const isChanged = (id: number) => filled(guesses[id]) && !same(guesses[id], saved[id])
  const changed = entries.filter(({ match, state }) => state === 'open' && isChanged(match.id))
  const done = entries.filter(({ match }) => filled(saved[match.id])).length

  async function save() {
    setSaving(true)
    setError('')
    try {
      const rows = await apiFetch<Prediction[]>('/predictions/bulk', {
        method: 'POST',
        body: {
          predictions: changed.map(({ match }) => ({
            match: match.id,
            home_goals: Number(guesses[match.id].home),
            away_goals: Number(guesses[match.id].away),
          })),
        },
      })
      setSaved((current) => {
        const next = { ...current }
        for (const row of rows) next[row.match] = { home: String(row.home_goals), away: String(row.away_goals) }
        return next
      })
    } catch (caught) {
      setError(caught instanceof ApiError ? errorDetail(caught, caught.message) : '')
      if (caught instanceof ApiError && caught.data?.code === 'prediction_locked') router.refresh()
    } finally {
      setSaving(false)
    }
  }

  const arrow = 'flex size-9 items-center justify-center rounded-xl border border-border bg-surface2 text-lg'

  return (
    <div className="space-y-4">
      <Card padding="md" className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div className="flex items-center gap-3">
          {prevHref ? (
            <Link href={prevHref} scroll={false} aria-label={labels.previous} className={`${arrow} hover:border-accent/60`}>
              ‹
            </Link>
          ) : (
            <span aria-hidden="true" className={`${arrow} opacity-40`}>
              ‹
            </span>
          )}
          <h2 className="font-heading text-lg font-bold">{fill(labels.matchday, { n: matchday })}</h2>
          {nextHref ? (
            <Link href={nextHref} scroll={false} aria-label={labels.next} className={`${arrow} hover:border-accent/60`}>
              ›
            </Link>
          ) : (
            <span aria-hidden="true" className={`${arrow} opacity-40`}>
              ›
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-muted">
          <span className="rounded-lg bg-surface2 px-3 py-1.5">
            {labels.exact_score} <b className="text-lime">+3</b>
          </span>
          <span className="rounded-lg bg-surface2 px-3 py-1.5">
            {labels.right_result} <b className="text-lime">+1</b>
          </span>
        </div>
        <div className="ml-auto w-full min-w-40 space-y-1.5 sm:w-48">
          <p className="text-right text-xs text-muted">{fill(labels.predicted_of, { done, total: entries.length })}</p>
          <ProgressBar value={entries.length ? done / entries.length : 0} />
        </div>
      </Card>

      {entries.length === 0 ? (
        <p className="text-sm text-muted">{labels.no_matches}</p>
      ) : (
        <Card padding="none" className="overflow-hidden">
          <ul>
            {entries.map((entry) => (
              <PredictionRow
                key={entry.match.id}
                entry={entry}
                guess={guesses[entry.match.id]}
                onGuess={(guess) => setGuesses((current) => ({ ...current, [entry.match.id]: guess }))}
                changed={isChanged(entry.match.id)}
                saved={filled(saved[entry.match.id])}
                labels={labels}
                today={today}
              />
            ))}
          </ul>
        </Card>
      )}

      {entries.some(({ state }) => state === 'open') && (
        <Card padding="md" className="flex flex-wrap items-center justify-between gap-3">
          <p className="min-w-0 text-sm text-muted" role="status">
            {error ||
              (changed.length > 0 ? fill(labels.unsaved_changes, { count: changed.length }) : labels.all_saved)}
          </p>
          <Button size="lg" disabled={changed.length === 0 || saving} onClick={save} className="w-full sm:w-72">
            {saving ? labels.saving : labels.save_predictions}
          </Button>
        </Card>
      )}
    </div>
  )
}
