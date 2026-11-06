'use client'

import { useState } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { BODY_MAX, length } from '@/lib/forums'
import type { ForumLabels, ForumPost } from '@/types/forums'

interface ReplyBoxProps {
  topic: number
  labels: ForumLabels
  value: string
  onChange: (value: string) => void
  predicted: string | null // "Newcastle 1 – 3 Arsenal": the player's own prediction for the topic's match, if any
  serverUnreachable: string
  onPosted: (post: ForumPost) => void
}

// The reply box (design 12). The server checks everything again (length after trimming, links, banned words,
// the 30 second limit, a ban) and answers with a coded error in the player's language; this only shows it.
export default function ReplyBox({ topic, labels, value, onChange, predicted, serverUnreachable, onPosted }: ReplyBoxProps) {
  const [attach, setAttach] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const size = length(value)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (pending) return
    setPending(true)
    setError('')
    try {
      const post = await apiFetch<ForumPost>('/posts', {
        method: 'POST',
        body: { topic, body: value, ...(attach && { attach_prediction: true }) },
      })
      onChange('')
      setAttach(false)
      onPosted(post)
    } catch (caught) {
      setError(caught instanceof ApiError ? errorDetail(caught, serverUnreachable) : serverUnreachable)
    } finally {
      setPending(false)
    }
  }

  return (
    <Card as="div" padding="md">
      <form onSubmit={submit} className="space-y-3">
        <textarea
          id="reply-box"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={labels.write_reply}
          aria-label={labels.write_reply}
          rows={4}
          className="w-full resize-y rounded-xl border border-border bg-surface2 px-4 py-3 text-sm text-text outline-none placeholder:text-muted focus:border-accent"
        />
        {predicted && (
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={attach}
              onChange={(event) => setAttach(event.target.checked)}
              className="mt-1 size-4 accent-lime"
            />
            <span>
              {labels.attach_prediction}
              <span className="block text-xs text-muted">{predicted}</span>
            </span>
          </label>
        )}
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="min-w-0 text-xs text-muted">
            {labels.reply_hint} ·{' '}
            <span className={size > BODY_MAX ? 'text-danger' : ''}>
              {size}/{BODY_MAX}
            </span>
          </p>
          <Button type="submit" disabled={size === 0 || pending}>
            {pending ? labels.posting : labels.post_reply}
          </Button>
        </div>
      </form>
    </Card>
  )
}
