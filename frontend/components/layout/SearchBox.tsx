'use client'

import { useSearchParams } from 'next/navigation'
import { useState } from 'react'
import { LOBBY_PATH } from '@/lib/games'

// Lives only in the lobby's top bar (HeaderTitle), so it filters the lobby in place.
export default function SearchBox({ placeholder }: { placeholder: string }) {
  const searchParams = useSearchParams()
  const query = searchParams.get('q') ?? ''
  const [value, setValue] = useState(query)
  const [lastQuery, setLastQuery] = useState(query)

  // A link can change ?q= from outside: the box follows it.
  if (query !== lastQuery) {
    setLastQuery(query)
    setValue(query)
  }

  function search(text: string) {
    setValue(text)

    const params = new URLSearchParams(searchParams)
    if (text) params.set('q', text)
    else params.delete('q')

    // The lobby filters on the client, so typing doesn't need a request to the server.
    window.history.replaceState(null, '', params.size > 0 ? `${LOBBY_PATH}?${params}` : LOBBY_PATH)
  }

  return (
    <input
      type="search"
      value={value}
      onChange={(event) => search(event.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className="h-11 w-full rounded-xl border border-border bg-surface px-4 text-sm text-text outline-none placeholder:text-muted focus:border-accent"
    />
  )
}
