'use client'

import { useWatchOdds } from './SlipProvider'

// Keeps the odds of what a page shows fresh (polled every 30 s while the tab is open).
export default function WatchOdds({ query }: { query: string }) {
  useWatchOdds(query)
  return null
}
