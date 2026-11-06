import type { LiveMatch, LiveMessage, LiveRow } from '@/types/live'

// The live scores are a public, cookie-free feed: the browser connects to Django directly (like the
// crash and roulette feeds). It is display only: a live score never settles a bet or a prediction.
export const SPORTS_WS_URL = process.env.NEXT_PUBLIC_SPORTS_WS_URL ?? 'ws://127.0.0.1:8000/ws/sports'

export type LiveState = Record<number, LiveMatch>

// The page renders from the REST list, whose club names are in the page's language.
export function fromRows(rows: LiveRow[]): LiveState {
  const state: LiveState = {}
  for (const row of rows) {
    state[row.match.id] = {
      match: row.match.id,
      competition: row.match.competition,
      kickoff: row.match.kickoff,
      home: row.match.home,
      away: row.match.away,
      status: row.status,
      minute: row.minute,
      home_score: row.home_score,
      away_score: row.away_score,
      delayed: row.delayed,
      goal_at: row.goal_at,
    }
  }
  return state
}

// A feed message carries English club names. A match we already show keeps its translated names;
// only a match that is new to the page takes the feed's.
function merge(known: LiveMatch | undefined, row: LiveMatch): LiveMatch {
  const { match, competition, kickoff, home, away, status, minute, home_score, away_score, delayed, goal_at } = row
  return {
    match,
    competition,
    kickoff,
    home: known?.home ?? home,
    away: known?.away ?? away,
    status,
    minute,
    home_score,
    away_score,
    delayed,
    goal_at,
  }
}

export function reduceLive(state: LiveState, message: LiveMessage): LiveState {
  switch (message.type) {
    case 'snapshot': {
      // A new connection tells everything in play now, so what is missing from it has ended.
      const next: LiveState = {}
      for (const row of message.matches) next[row.match] = merge(state[row.match], row)
      return next
    }
    case 'remove': {
      const next = { ...state }
      delete next[message.match]
      return next
    }
    default:
      return { ...state, [message.match]: merge(state[message.match], message) }
  }
}

export function sortedLive(state: LiveState) {
  return Object.values(state).sort((a, b) => a.kickoff.localeCompare(b.kickoff) || a.match - b.match)
}
