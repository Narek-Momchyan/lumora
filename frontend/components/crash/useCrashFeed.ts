'use client'

import { useEffect, useReducer, useRef, useState } from 'react'
import { HISTORY_LENGTH, RECONNECT_MAX_MS, RECONNECT_MIN_MS, WS_URL } from '@/lib/crash'
import type { CrashMessage, CrashPoint, CrashRound, LiveBet } from '@/types/crash'

interface FeedState {
  round: CrashRound | null
  history: CrashPoint[]
  bets: LiveBet[]
}

const EMPTY: FeedState = { round: null, history: [], bets: [] }

function upsertBet(bets: LiveBet[], bet: LiveBet) {
  return bets.some(({ id }) => id === bet.id) ? bets.map((row) => (row.id === bet.id ? bet : row)) : [...bets, bet]
}

function reduce(state: FeedState, message: CrashMessage): FeedState {
  switch (message.type) {
    case 'snapshot':
      return { round: message.round, history: message.history, bets: message.bets }
    case 'round.betting':
      return { ...state, round: message, bets: [] }
    case 'round.flying':
      return { ...state, round: message }
    case 'round.crashed': {
      const point = { number: message.number, crash_point: message.crash_point ?? '' }
      const known = state.history[0]?.number === message.number
      return {
        ...state,
        round: message,
        history: known ? state.history : [point, ...state.history].slice(0, HISTORY_LENGTH),
      }
    }
    case 'bet.placed':
    case 'bet.cashed_out':
      return message.round === state.round?.number ? { ...state, bets: upsertBet(state.bets, message) } : state
  }
}

// The live round from /ws/crash. A lost connection comes back by itself, and the snapshot of the
// new connection fills in everything that was missed.
export default function useCrashFeed() {
  const [feed, dispatch] = useReducer(reduce, EMPTY)
  const [connected, setConnected] = useState(false)
  const clockOffset = useRef<number | null>(null)

  useEffect(() => {
    let socket: WebSocket
    let retry: ReturnType<typeof setTimeout>
    let delay = RECONNECT_MIN_MS
    let stopped = false

    function connect() {
      socket = new WebSocket(WS_URL)

      socket.onopen = () => {
        delay = RECONNECT_MIN_MS
        clockOffset.current = null
        setConnected(true)
      }

      socket.onmessage = ({ data }) => {
        const message: CrashMessage = JSON.parse(data)
        if ('server_time' in message) {
          // A message arrives late, never early, so the largest offset is the closest to the truth.
          const offset = Date.parse(message.server_time) - Date.now()
          clockOffset.current = Math.max(clockOffset.current ?? offset, offset)
        }
        dispatch(message)
      }

      socket.onclose = () => {
        setConnected(false)
        if (stopped) return
        retry = setTimeout(connect, delay)
        delay = Math.min(delay * 2, RECONNECT_MAX_MS)
      }
    }

    connect()

    return () => {
      stopped = true
      clearTimeout(retry)
      socket.close()
    }
  }, [])

  return { ...feed, connected, clockOffset }
}
