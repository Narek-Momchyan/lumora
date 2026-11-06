'use client'

import { useState } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { TOPICS_PAGE, cursor } from '@/lib/forums'
import type { ForumLabels, ForumTopic, TopicSort } from '@/types/forums'
import TopicRow from './TopicRow'

interface TopicListProps {
  initial: ForumTopic[] // the first page, rendered by the server
  forum: number
  tag: string
  sort: TopicSort
  labels: ForumLabels
  serverUnreachable: string
}

// The topics of a club. The server renders the first 50; "Load more" asks for the next 50 with the cursor
// of the last row (only the "latest" sort can page: the others return their top 50). After a new topic the
// page asks the server again and the parent gives this list a new key, so it starts from the fresh page.
export default function TopicList({ initial, forum, tag, sort, labels, serverUnreachable }: TopicListProps) {
  const [rows, setRows] = useState(initial)
  const [more, setMore] = useState(sort === 'latest' && initial.length >= TOPICS_PAGE)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function loadMore() {
    setLoading(true)
    setError('')
    try {
      const query = new URLSearchParams({ forum: String(forum), sort, before: cursor(rows[rows.length - 1]), ...(tag && { tag }) })
      const next = await apiFetch<ForumTopic[]>(`/topics?${query}`)
      setRows((current) => [...current, ...next])
      setMore(next.length >= TOPICS_PAGE)
    } catch (caught) {
      setError(caught instanceof ApiError ? errorDetail(caught, serverUnreachable) : serverUnreachable)
    } finally {
      setLoading(false)
    }
  }

  if (rows.length === 0) return <p className="text-sm text-muted">{labels.no_topics}</p>

  return (
    <div className="space-y-3">
      <Card padding="none" className="overflow-hidden">
        <ul>
          {rows.map((topic) => (
            <TopicRow key={topic.id} topic={topic} labels={labels} />
          ))}
        </ul>
      </Card>
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
    </div>
  )
}
