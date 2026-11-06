import type { Match, Team } from './sports'

// Mirrors backend sports/models.py LiveLabel: every text of the live page.
export interface LiveLabels {
  page_text: string
  live: string
  half_time: string
  full_time: string
  minute: string // "{minute}'"
  goal: string
  delayed: string
  delayed_note: string
  no_live: string
  live_count: string // "{count} live"
  reconnecting: string
}

export type LiveStatus = 'live' | 'half_time' | 'ended'

// One match in play, as the /ws/sports feed sends it (backend sports/feed.py live_data).
export type LiveTeam = Pick<Team, 'id' | 'name' | 'short_name' | 'tla' | 'color' | 'text_color' | 'crest'>

export interface LiveMatch {
  match: number
  competition: string
  kickoff: string
  home: LiveTeam
  away: LiveTeam
  status: LiveStatus
  minute: number | null
  home_score: number
  away_score: number
  delayed: boolean // the score comes from football-data.org and can be minutes behind
  goal_at: string | null
}

export type LiveMessage =
  | { type: 'snapshot'; matches: LiveMatch[]; server_time: string }
  | ({ type: 'score' | 'minute' | 'status'; goal: boolean } & LiveMatch)
  | { type: 'remove'; match: number }

// One row of GET /api/live_matches (names in the page's language).
export interface LiveRow {
  id: number
  match: Match
  status: LiveStatus
  minute: number | null
  home_score: number
  away_score: number
  source: 'api_football' | 'football_data'
  delayed: boolean
  goal_at: string | null
  updated_at: string
}
