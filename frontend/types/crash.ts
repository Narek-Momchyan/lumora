export interface CrashPageLabels {
  id: number
  lang: string
  page_title: string
  page_description: string
  game_title: string
  tab_manual: string
  tab_auto: string
  bet_amount: string
  bet_half: string
  bet_double: string
  bet_plus: string
  bet_max: string
  auto_cash_out_at: string
  place_bet: string
  bet_placed: string
  cash_out: string
  cashed_out: string
  betting_status: string
  flying_status: string
  crashed_status: string
  waiting_status: string
  live_bets: string
  players_count: string
  bet_lost: string
  bot_badge: string
  history_title: string
  round_number: string
  provably_fair: string
  house_edge: string
  seed_label: string
  seed_hash_label: string
  commitment_label: string
  connecting: string
  server_unreachable: string
}

// `crash_point`, `seed` and `crashed_at` exist only after the crash.
export interface CrashRound {
  number: number
  status: 'betting' | 'flying' | 'crashed'
  seed_hash: string
  betting_ends_at: string
  started_at: string | null
  server_time: string
  crash_point?: string
  seed?: string
  crashed_at?: string
}

export interface CrashPoint {
  number: number
  crash_point: string
}

// A bet in the live feed: `id` is "player-<bet id>" or "bot-<id>".
export interface LiveBet {
  id: string
  round: number
  player: string
  amount: string
  multiplier: string | null
  payout: string
  is_bot: boolean
}

export type CrashMessage =
  | { type: 'snapshot'; round: CrashRound | null; history: CrashPoint[]; bets: LiveBet[]; server_time: string }
  | ({ type: 'round.betting' | 'round.flying' | 'round.crashed' } & CrashRound)
  | ({ type: 'bet.placed' | 'bet.cashed_out' } & LiveBet)

// The player's own bet, from /api/crash_bets.
export interface CrashBet {
  id: number
  round: number
  amount: string
  target: string | null
  status: 'active' | 'cashed_out' | 'lost'
  multiplier: string | null
  payout: string
  created_at: string
}

export interface CrashBetResult extends CrashBet {
  balance: string
}
