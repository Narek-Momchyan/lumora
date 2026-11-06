'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import Button from '@/components/ui/Button'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { POSTS_PAGE, mergePosts } from '@/lib/forums'
import type { ForumLabels, ForumPost } from '@/types/forums'
import PostCard from './PostCard'
import ReplyBox from './ReplyBox'

interface PostListProps {
  topic: number
  initial: ForumPost[] // the first page, rendered by the server
  locked: boolean
  predicted: string | null
  labels: ForumLabels
  serverUnreachable: string
}

// The posts of a topic and the reply box. The server renders the first 100; "Load more" asks for the next
// ones after the last post it has LOADED. A reply the player posts is added to the list but does not move
// that cursor, and every list is merged by post id: the reply never shows twice if it is also in a later
// page, and no post between the pages is skipped.
export default function PostList({ topic, initial, locked, predicted, labels, serverUnreachable }: PostListProps) {
  const router = useRouter()
  const [posts, setPosts] = useState(initial)
  const [cursor, setCursor] = useState(initial.length ? initial[initial.length - 1].id : 0) // last LOADED post
  const [more, setMore] = useState(initial.length >= POSTS_PAGE)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [reply, setReply] = useState('')

  async function loadMore() {
    setLoading(true)
    setError('')
    try {
      const next = await apiFetch<ForumPost[]>(`/posts?topic=${topic}&after=${cursor}`)
      setPosts((current) => mergePosts(current, next))
      if (next.length) setCursor(next[next.length - 1].id)
      setMore(next.length >= POSTS_PAGE)
    } catch (caught) {
      setError(caught instanceof ApiError ? errorDetail(caught, serverUnreachable) : serverUnreachable)
    } finally {
      setLoading(false)
    }
  }

  function quote(name: string) {
    setReply((current) => `${current}${current && !current.endsWith(' ') ? ' ' : ''}@${name} `)
    document.getElementById('reply-box')?.focus()
  }

  function posted(post: ForumPost) {
    setPosts((current) => mergePosts(current, [post]))
    router.refresh() // the counts in the header and the side card come from the server
  }

  return (
    <div className="space-y-4">
      {posts.map((post) => (
        <PostCard key={post.id} post={post} labels={labels} serverUnreachable={serverUnreachable} onReply={quote} />
      ))}

      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
      {more && (
        <Button variant="ghost" block disabled={loading} onClick={loadMore}>
          {labels.load_more}
        </Button>
      )}

      {locked ? (
        <p className="rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-muted">{labels.topic_locked_note}</p>
      ) : (
        <ReplyBox
          topic={topic}
          labels={labels}
          value={reply}
          onChange={setReply}
          predicted={predicted}
          serverUnreachable={serverUnreachable}
          onPosted={posted}
        />
      )}
    </div>
  )
}
