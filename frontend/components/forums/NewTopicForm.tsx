'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Chip from '@/components/ui/Chip'
import Field from '@/components/ui/Field'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { BODY_MAX, TAGS, TITLE_MAX, length, tagLabel } from '@/lib/forums'
import type { ForumLabels, TopicTag } from '@/types/forums'

export interface PredictedMatch {
  id: number
  home: string
  away: string
  score: string // "2 – 1": the player's own prediction
}

interface NewTopicFormProps {
  forum: number
  labels: ForumLabels
  predicted: PredictedMatch | null // the club's next match, only when the player has a prediction for it
  serverUnreachable: string
  onDone: () => void
}

// The "New topic" form. The server checks everything again (length after trimming, links, banned words,
// the 30 second and 10-a-day limits, a ban) and answers with a coded error whose text is in the player's
// language; this form only shows it. After a topic is created the list is refreshed in place.
export default function NewTopicForm({ forum, labels, predicted, serverUnreachable, onDone }: NewTopicFormProps) {
  const router = useRouter()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [tag, setTag] = useState<TopicTag>('match_talk')
  const [attach, setAttach] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  const titleLength = length(title)
  const bodyLength = length(body)
  const ready = titleLength > 0 && bodyLength > 0 && !pending

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setPending(true)
    setError('')
    try {
      await apiFetch('/topics', {
        method: 'POST',
        body: { forum, title, tag, body, ...(attach && predicted && { match: predicted.id, attach_prediction: true }) },
      })
      onDone()
      router.refresh() // the list asks the server again; the new topic is in it
    } catch (caught) {
      setError(caught instanceof ApiError ? errorDetail(caught, serverUnreachable) : serverUnreachable)
      setPending(false)
    }
  }

  const counter = (value: number, max: number) => (
    <span className={`text-xs tabular-nums ${value > max ? 'text-danger' : 'text-muted'}`}>
      {value}/{max}
    </span>
  )

  return (
    <Card as="div" padding="md">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <Field id="topic-title" label={labels.topic_title} value={title} onChange={(event) => setTitle(event.target.value)} autoComplete="off" />
          <div className="mt-1 text-right">{counter(titleLength, TITLE_MAX)}</div>
        </div>

        <div>
          <p className="mb-2 text-xs text-muted lg:text-[13px]">{labels.topic_tag}</p>
          <div className="flex flex-wrap gap-2">
            {TAGS.map((item) => (
              <Chip key={item} active={tag === item} onClick={() => setTag(item)}>
                {tagLabel(item, labels)}
              </Chip>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="topic-body" className="mb-2 block text-xs text-muted lg:text-[13px]">
            {labels.topic_body}
          </label>
          <textarea
            id="topic-body"
            value={body}
            onChange={(event) => setBody(event.target.value)}
            rows={5}
            className="w-full resize-y rounded-xl border border-border bg-surface2 px-4 py-3 text-sm text-text outline-none placeholder:text-muted focus:border-accent"
          />
          <div className="mt-1 text-right">{counter(bodyLength, BODY_MAX)}</div>
        </div>

        {predicted && (
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" checked={attach} onChange={(event) => setAttach(event.target.checked)} className="mt-1 size-4 accent-lime" />
            <span>
              {labels.attach_prediction}
              <span className="block text-xs text-muted">
                {predicted.home} {predicted.score} {predicted.away}
              </span>
            </span>
          </label>
        )}

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="ghost" onClick={onDone}>
            {labels.cancel}
          </Button>
          <Button type="submit" disabled={!ready}>
            {pending ? labels.posting : labels.create_topic}
          </Button>
        </div>
      </form>
    </Card>
  )
}
