'use client'

import { useReducer } from 'react'
import { SPORTS_WS_URL, reduceLive, type LiveState } from '@/lib/live'
import useLiveSocket from '@/lib/useLiveSocket'
import type { LiveMessage } from '@/types/live'

// The matches in play: the page's own list first, then every change from /ws/sports. A lost
// connection comes back by itself and its snapshot fills in what was missed.
export default function useLiveMatches(initial: LiveState) {
  const [matches, dispatch] = useReducer(reduceLive, initial)
  const { connected } = useLiveSocket<LiveMessage>(SPORTS_WS_URL, dispatch)
  return { matches, connected }
}
