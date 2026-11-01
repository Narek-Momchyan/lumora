'use client'

import { useReducer } from 'react'
import { HISTORY_LENGTH, WS_URL } from '@/lib/crash'
import useLiveSocket from '@/lib/useLiveSocket'
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

export default function useCrashFeed() {
  const [feed, dispatch] = useReducer(reduce, EMPTY)
  const { connected, clockOffset } = useLiveSocket<CrashMessage>(WS_URL, dispatch)

  return { ...feed, connected, clockOffset }
}
