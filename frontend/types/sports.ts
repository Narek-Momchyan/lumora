export interface SportsPageLabels {
  id: number
  lang: string
  page_title: string
  page_description: string
  hero_eyebrow: string
  hero_title: string
  hero_text: string
}

// The texts of the football pages, bet slip and My bets. {n}-style placeholders are filled in the UI.
export interface SportsUiLabels {
  id: number
  lang: string
  matchday_label: string
  starts_in: string
  today: string
  tomorrow: string
  live_now: string
  matches_count: string
  bets_close_at_kickoff: string
  markets_more: string
  lumora_model: string
  win_chance: string
  odds_note: string
  no_matches: string
  no_odds_yet: string
  slip_title: string
  slip_empty_title: string
  slip_empty_text: string
  clear_all: string
  total_odds: string
  stake_label: string
  potential_win: string
  place_bet: string
  accept_odds: string
  bet_placed: string
  closed_badge: string
  odds_changed_note: string
  max_button: string
  min_picks: string
  popular_title: string
  model_card_title: string
  model_card_text: string
  all_markets: string
  main_markets: string
  goals_markets: string
  score_markets: string
  markets_total: string
  over_short: string
  under_short: string
  pays_up_to: string
  tab_all: string
  tab_open: string
  tab_settled: string
  this_week: string
  staked: string
  returned: string
  profit: string
  won_bets: string
  won_of: string
  odds_label: string
  stake_short: string
  empty_my_bets: string
  profit_by_day: string
  profit_by_day_note: string
  weekdays_short: string
  form_win: string
  form_draw: string
  form_loss: string
  ticket_id: string
  full_time_short: string
  standing_line: string
  popular_odds_hint: string
  server_unreachable: string
}

export interface BetLabels {
  id: number
  lang: string
  match_result: string
  double_chance: string
  total_goals: string
  both_teams_to_score: string
  correct_score: string
  home: string
  draw: string
  away: string
  home_or_draw: string
  home_or_away: string
  draw_or_away: string
  over: string
  under: string
  yes: string
  no: string
  other_score: string
  single: string
  express: string
  status_open: string
  status_won: string
  status_lost: string
  status_void: string
  model_label: string
}

export interface Team {
  id: number
  name: string
  short_name: string
  tla: string
  color: string
  text_color: string
  crest: string | null
}

export type MatchStatus =
  | 'scheduled'
  | 'live'
  | 'paused'
  | 'finished'
  | 'postponed'
  | 'suspended'
  | 'cancelled'
  | 'awarded'

export interface Match {
  id: number
  competition: string
  matchday: number | null
  stage: string
  group: string
  home: Team
  away: Team
  kickoff: string
  status: MatchStatus
  duration: string
  home_score: number | null
  away_score: number | null
  home_regular: number | null
  away_regular: number | null
  market_count: number
}

export interface TableRow {
  position: number
  points: number
}

export interface MatchDetail extends Match {
  home_form: string[]
  away_form: string[]
  home_table: TableRow | null
  away_table: TableRow | null
}

export interface Competition {
  id: number
  code: string
  name: string
  flag: string | null
  order: number
}

export type MarketKind = '1x2' | 'double_chance' | 'total' | 'btts' | 'correct_score'

export interface Selection {
  id: number
  code: string
  odds: string
  previous_odds: string | null
  probability: string
  result: 'pending' | 'won' | 'lost' | 'void'
}

export interface Market {
  id: number
  match: number
  kind: MarketKind
  line: string | null
  status: 'open' | 'closed' | 'settled' | 'void'
  selections: Selection[]
}

export interface PopularPick {
  id: number
  market: MarketKind
  line: string | null
  code: string
  odds: string
  previous_odds: string | null
  match: Match
  picks: number
}

export interface BetPickRow {
  id: number
  selection: number
  market: MarketKind
  line: string | null
  code: string
  odds: string
  result: Selection['result']
  match: Match
}

export interface Bet {
  id: number
  key: string
  kind: 'single' | 'express'
  stake: string
  total_odds: string
  potential_win: string
  status: 'open' | 'won' | 'lost' | 'void'
  payout: string
  created_at: string
  settled_at: string | null
  picks: BetPickRow[]
}

export interface BetSummary {
  staked: string
  returned: string
  profit: string
  won: number
  open: number
  bets: number
  by_day: { date: string; profit: string }[]
}
