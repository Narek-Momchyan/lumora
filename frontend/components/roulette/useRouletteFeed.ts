'use client'

import { useReducer } from 'react'
import { WS_URL } from '@/lib/roulette'
import useLiveSocket from '@/lib/useLiveSocket'
import type { RouletteMessage, RouletteResult, RouletteRound, SeatPayout, TableBet } from '@/types/roulette'

const HISTORY_LENGTH = 14

interface FeedState {
  round: RouletteRound | null
  history: RouletteResult[]
  bets: TableBet[]
  payouts: SeatPayout[]
}

const EMPTY: FeedState = { round: null, history: [], bets: [], payouts: [] }

function upsertBet(bets: TableBet[], bet: TableBet) {
  return bets.some(({ id }) => id === bet.id) ? bets.map((row) => (row.id === bet.id ? bet : row)) : [...bets, bet]
}

function reduce(state: FeedState, message: RouletteMessage): FeedState {
  switch (message.type) {
    case 'snapshot':
      return { round: message.round, history: message.history, bets: message.bets, payouts: [] }
    case 'round.betting':
      return { ...state, round: message, bets: [], payouts: [] }
    case 'round.spinning':
      return { ...state, round: message }
    case 'round.settled': {
      const point = { number: message.number, result: message.result ?? 0, color: message.color ?? 'green' }
      const known = state.history[0]?.number === message.number
      return {
        ...state,
        round: message,
        payouts: message.payouts,
        history: known ? state.history : [point, ...state.history].slice(0, HISTORY_LENGTH),
      }
    }
    case 'bet.placed':
      return message.round === state.round?.number ? { ...state, bets: upsertBet(state.bets, message) } : state
  }
}

export default function useRouletteFeed() {
  const [feed, dispatch] = useReducer(reduce, EMPTY)
  const { connected, clockOffset } = useLiveSocket<RouletteMessage>(WS_URL, dispatch)

  // A snapshot sent during a spin already has this round: it must not show before the ball stops.
  const history = feed.history.filter(
    ({ number }) => !(feed.round?.status === 'spinning' && number === feed.round.number),
  )

  return { ...feed, history, connected, clockOffset }
}
