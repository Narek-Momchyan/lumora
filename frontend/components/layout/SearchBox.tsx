'use client'

import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'

export default function SearchBox({ placeholder }: { placeholder: string }) {
  const router = useRouter()
  const pathname = usePathname()
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
    const url = params.size > 0 ? `/?${params}` : '/'

    // The lobby filters on the client, so typing doesn't need a request to the server.
    if (pathname === '/') window.history.replaceState(null, '', url)
    else router.push(url)
  }

  return (
    <input
      type="search"
      value={value}
      onChange={(event) => search(event.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text outline-none placeholder:text-muted focus:border-cyan"
    />
  )
}
