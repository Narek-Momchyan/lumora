'use client'

import { useState } from 'react'
import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'
import { ApiError, apiFetch } from '@/lib/api'
import { authorName, ruleLabel } from '@/lib/forums'
import { fill, teamName } from '@/lib/sports'
import type { ForumLabels, ForumPost } from '@/types/forums'
import LocalTime from './LocalTime'
import ReportMenu from './ReportMenu'

interface PostCardProps {
  post: ForumPost
  labels: ForumLabels
  serverUnreachable: string
  onReply: (name: string) => void
}

// One post (design 12). Player text is shown only as text (pre-wrapped, never as HTML). A post a moderator
// hid arrives without its text, so there is nothing to show but the moderator's note and the rule. A like
// is sent once at a time (the button waits for the answer), and the server counts one like per player.
export default function PostCard({ post, labels, serverUnreachable, onReply }: PostCardProps) {
  const [likes, setLikes] = useState(post.likes)
  const [liked, setLiked] = useState(post.liked_by_me)
  const [pending, setPending] = useState(false)
  const name = authorName(post.author.name, labels)

  async function toggleLike() {
    if (pending) return
    setPending(true)
    try {
      const row = await apiFetch<{ likes: number; liked_by_me: boolean }>(`/posts/${post.id}/like`, {
        method: liked ? 'DELETE' : 'POST',
      })
      setLikes(row.likes)
      setLiked(row.liked_by_me)
    } catch (caught) {
      if (!(caught instanceof ApiError)) throw caught // a refused like (a hidden post, a ban) changes nothing
    } finally {
      setPending(false)
    }
  }

  if (post.hidden) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-dashed border-border px-4 py-3 text-sm text-muted">
        <span aria-hidden="true">⊘</span>
        <span>
          {labels.hidden_by_moderator}
          {post.hidden_rule && ` · ${fill(labels.hidden_rule, { rule: ruleLabel(post.hidden_rule, labels) })}`}
        </span>
      </div>
    )
  }

  return (
    <Card as="article" padding="md" className="space-y-3">
      <header className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <span
          aria-hidden="true"
          className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent/20 text-sm font-bold text-accent uppercase"
        >
          {[...name][0]}
        </span>
        <span className="min-w-0 truncate text-sm font-semibold">{name}</span>
        {post.is_author && (
          <Badge small tone="accent">
            {labels.author_tag}
          </Badge>
        )}
        {post.top_predictor && (
          <Badge small tone="lime">
            ★ {labels.top_predictor}
          </Badge>
        )}
        <LocalTime value={post.created_at} className="text-xs text-muted" />
      </header>

      <p className="text-sm leading-relaxed break-words whitespace-pre-wrap">{post.body}</p>

      {post.prediction && (
        <p className="inline-flex max-w-full items-center rounded-xl border border-border bg-surface2 px-3 py-2 text-xs">
          {fill(labels.prediction_in_post, {
            home: teamName(post.prediction.home),
            score: `${post.prediction.home_goals} – ${post.prediction.away_goals}`,
            away: teamName(post.prediction.away),
          })}
        </p>
      )}

      <footer className="flex items-center justify-between gap-3 text-xs">
        <span className="flex items-center gap-4">
          <button
            type="button"
            onClick={toggleLike}
            disabled={pending}
            aria-pressed={liked}
            aria-label={labels.like}
            className={`inline-flex items-center gap-1 tabular-nums transition-colors disabled:opacity-60 ${liked ? 'text-lime' : 'text-muted hover:text-text'}`}
          >
            ♥ {likes}
          </button>
          <button type="button" onClick={() => onReply(name)} className="text-muted transition-colors hover:text-text">
            {labels.reply}
          </button>
        </span>
        {!post.is_mine && <ReportMenu post={post.id} labels={labels} serverUnreachable={serverUnreachable} />}
      </footer>
    </Card>
  )
}
