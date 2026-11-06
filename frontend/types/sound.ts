// One sound of Neon Crash or Lumora Roulette (GET /api/game_sounds): only active ones that have a file.
export interface GameSound {
  code: string
  file: string
}

// The keys the pages use. A key without an uploaded file is silently skipped.
export type SoundCode =
  | 'crash_flight'
  | 'crash_boom'
  | 'cash_out'
  | 'bet_placed'
  | 'round_start'
  | 'roulette_spin'
  | 'roulette_ball_drop'
  | 'win'
  | 'lose'

// The texts of the sound button, from the page's labels (Neon Crash and Roulette each have them).
export interface SoundLabels {
  sound_on: string // the button while the sound is off: turn it on
  sound_off: string // the button while the sound is on: mute it
  sound_volume: string // the volume slider
}
