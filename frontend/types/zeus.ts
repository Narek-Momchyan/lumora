export interface SlotSymbol {
  id: number
  code: string
  image: string | null
  order: number
}

export interface SlotSymbolName {
  id: number
  symbol: string
  lang: string
  name: string
}

export interface SlotSound {
  code: string
  file: string
}

export interface JackpotPool {
  tier: string
  amount: string
}

// Pays are in hundredths of the bet: 150 is 1.5x.
export interface SlotStep {
  grid: string[][]
  wins: { symbol: string; count: number; pay: number }[]
  winning_cells: [number, number][]
  pay: number
  running_win: number
}

export interface SlotRoundSpin {
  is_free_spin: boolean
  steps: SlotStep[]
  scatter_win: number
  collected_multipliers: number[]
  global_multiplier: number
  win: number
  free_spins_awarded: number
  free_spins_left: number
  is_max_win: boolean
}

export interface SlotRound {
  spins: SlotRoundSpin[]
  total_win: number
  free_spins_played: number
  bonus_buy: boolean
}

export interface SlotSpinRecord {
  id: number
  game: string
  amount: string
  cost: string
  bonus_buy: boolean
  payout: string
  free_spins_played: number
  jackpot_tier: string
  jackpot_win: string
  server_seed_hash: string
  client_seed: string
  nonce: number
  created_at: string
}

export interface SlotSpinResponse extends SlotSpinRecord {
  result: SlotRound
  balance: string
  jackpot_pools: Record<string, string>
}

export interface ZeusPageLabels {
  id: number
  lang: string
  page_title: string
  page_description: string
  tagline: string
  free_spins_title: string
  free_spins_left: string
  tumble: string
  multiplier_total: string
  multiplier_collected: string
  balance: string
  last_win: string
  win: string
  bet: string
  bonus_bet: string
  speed_mode: string
  speed_normal: string
  speed_turbo: string
  speed_instant: string
  spin: string
  buy_bonus: string
  auto: string
  auto_spinning: string
  loading: string
  loading_tagline: string
  ready: string
  bonus_trigger: string
  congratulations: string
  total_win: string
  collect: string
  win_winning: string
  win_big: string
  win_super: string
  win_mega: string
  win_ultra: string
  win_max: string
  jackpot_mini: string
  jackpot_minor: string
  jackpot_major: string
  jackpot_grand: string
  jackpot_won: string
  server_unreachable: string
  free_spins_won: string
  buy_bonus_title: string
  buy_bonus_text: string
  buy_bonus_confirm: string
  cancel: string
  stop: string
  skip: string
  auto_spins_left: string
  auto_menu_label: string
  mute: string
  unmute: string
  bet_lower: string
  bet_raise: string
  jackpots_label: string
  history_title: string
  history_empty: string
  history_time: string
  history_cost: string
  history_win: string
  history_bonus_buy: string
  history_free_spins: string
  history_seed_hash: string
  history_client_seed: string
  history_nonce: string
  bonus_blessing: string
  bonus_begin: string
  bonus_complete: string
  tap_to_continue: string
  jackpot_icon_mini: string
  jackpot_icon_minor: string
  jackpot_icon_major: string
  jackpot_icon_grand: string
}

export type SymbolDetails = Record<string, { name: string; image: string | null }>
export type SpeedMode = 'normal' | 'turbo' | 'instant'

export type ZeusOverlay = { id: number } & (
  | { kind: 'bonus'; count: number }
  | { kind: 'summary'; payout: string }
  | { kind: 'big_win'; payout: string; amount: string }
  | { kind: 'jackpot'; tier: string; amount: string }
)

export interface SlotSoundPlayer {
  play: (code: string, loop?: boolean) => void
  stop: (code: string) => void
}
