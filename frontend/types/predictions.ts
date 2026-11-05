import type { Match, Team } from './sports'

// Mirrors backend sports/models.py PredictionLabel: every text of the predictions and league pages.
export interface PredictionLabels {
  exact_score: string
  right_result: string
  predicted_of: string
  matchday: string
  previous: string
  next: string
  saved: string
  not_saved: string
  locked: string
  live_score: string
  final_score: string
  exact_badge: string
  result_badge: string
  wrong_badge: string
  void_badge: string
  unsaved_changes: string
  all_saved: string
  save_predictions: string
  saving: string
  leaderboard: string
  players: string
  tab_matchday: string
  tab_season: string
  exact_short: string
  pts: string
  you: string
  your_season: string
  points: string
  rank: string
  exact_scores: string
  right_results: string
  empty_board: string
  no_matches: string
  predict_title: string
  predict_hint: string
  predict_save: string
  make_predictions: string
  open_left: string
  tab_matches: string
  tab_table: string
  tab_results: string
  season_after: string
  next_matchday: string
  col_club: string
  col_played: string
  col_won: string
  col_draw: string
  col_lost: string
  col_goals: string
  col_diff: string
  col_points: string
  col_form: string
  zone_champions_league: string
  zone_europa_league: string
  zone_conference_league: string
  zone_playoff: string
  zone_relegation: string
  no_results: string
}

export type PredictionOutcome = 'pending' | 'exact' | 'result' | 'wrong' | 'void'

export interface Prediction {
  id: number
  match: number
  home_goals: number
  away_goals: number
  outcome: PredictionOutcome
  points: number
  updated_at: string
}

export interface PredictionEntry {
  match: Match
  prediction: Prediction | null
  state: 'open' | 'locked' | 'scored'
}

export interface LeaderboardRow {
  rank: number
  user_id: number
  player: string
  points: number
  exact: number
  right: number
  played: number
}

export interface Leaderboard {
  players: number
  rows: LeaderboardRow[]
  me: LeaderboardRow | null
}

export interface PredictionStats {
  points: number
  rank: number | null
  exact: number
  right_percent: number
  played: number
  players: number
}

export interface Matchday {
  matchday: number
  matches: number
  open: number
  finished: number
  current: boolean
}

export type ZoneKind = 'champions_league' | 'europa_league' | 'conference_league' | 'playoff' | 'relegation'

export interface StandingZone {
  id: number
  kind: ZoneKind
  from_position: number
  to_position: number
}

export interface StandingRow {
  id: number
  stage: string
  group: string
  position: number
  team: Team
  played: number
  won: number
  draw: number
  lost: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
  form: string
}
