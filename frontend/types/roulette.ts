export interface RoulettePageLabels {
  id: number
  lang: string
  page_title: string
  page_description: string
  live: string
  players_count: string
  bets_close_in: string
  place_your_bets: string
  no_more_bets: string
  spinning: string
  result_in: string
  last_result: string
  winning_number: string
  you_won: string
  net_win: string
  bets_won: string
  your_bets: string
  bets_count: string
  chip_value: string
  undo: string
  clear: string
  double: string
  rebet: string
  total_bet: string
  total_win: string
  place_bets: string
  bets_closed: string
  live_table: string
  next_round_in: string
  you_badge: string
  bot_badge: string
  round_number: string
  provably_fair: string
  house_edge: string
  seed_label: string
  seed_hash_label: string
  commitment_label: string
  connecting: string
  server_unreachable: string
  color_red: string
  color_black: string
  color_green: string
  bet_straight: string
  bet_split: string
  bet_street: string
  bet_trio: string
  bet_corner: string
  bet_six_line: string
  bet_first_four: string
  bet_red: string
  bet_black: string
  bet_even: string
  bet_odd: string
  bet_low: string
  bet_high: string
  bet_dozen_1: string
  bet_dozen_2: string
  bet_dozen_3: string
  bet_column: string
  bet_column_short: string
}

export type PocketColor = 'red' | 'black' | 'green'

export interface BetSpot {
  bet_type: string
  value: number[]
}

// `result` and `color` exist from the spin on, `seed`, `settled_at` and `winning` after the settlement.
export interface RouletteRound {
  number: number
  status: 'betting' | 'spinning' | 'settled'
  seed_hash: string
  betting_ends_at: string
  server_time: string
  spin_started_at?: string
  spin_ends_at?: string
  result?: number
  color?: PocketColor
  seed?: string
  settled_at?: string
  winning?: BetSpot[]
}

export interface RouletteResult {
  number: number
  result: number
  color: PocketColor
}

export interface TableLine extends BetSpot {
  amount: string
}

// A slip at the table: `seat` is "player-<user id>" or "bot-<id>".
export interface TableBet {
  id: string
  round: number
  seat: string
  player: string
  is_bot: boolean
  amount: string
  payout: string
  lines: TableLine[]
}

export interface SeatPayout {
  seat: string
  player: string
  is_bot: boolean
  amount: string
  payout: string
}

export type RouletteMessage =
  | { type: 'snapshot'; round: RouletteRound | null; history: RouletteResult[]; bets: TableBet[]; server_time: string }
  | ({ type: 'round.betting' | 'round.spinning' } & RouletteRound)
  | ({ type: 'round.settled'; payouts: SeatPayout[] } & RouletteRound)
  | ({ type: 'bet.placed' } & TableBet)

// The player's own bets, from /api/roulette_bets.
export interface SlipLine extends TableLine {
  multiplier: number
  payout: string
}

export interface RouletteSlip {
  id: number
  round: number
  seat: string
  amount: string
  payout: string
  lines: SlipLine[]
  created_at: string
}

export interface RouletteSlipResult extends RouletteSlip {
  balance: string
}

export interface LastRound {
  round: number | null
  lines: SlipLine[]
}

// A bet on the board that isn't sent yet.
export interface DraftLine extends BetSpot {
  cents: number
}
