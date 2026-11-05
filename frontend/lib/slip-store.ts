import { SLIP_STORAGE_KEY } from './sports'
import type { MarketKind } from '@/types/sports'

// What a pick in the bet slip needs to show itself in any language and to be sent: the selection
// with the odds the player SAW (the backend compares them), and the match it belongs to.
export interface SlipPick {
  selection: number
  matchId: number
  kickoff: string
  kind: MarketKind
  line: string | null
  code: string
  odds: string
  home: string
  away: string
}

export type SlipMode = 'single' | 'express'

export interface SlipState {
  mode: SlipMode
  stake: string
  picks: SlipPick[]
}

const EMPTY: SlipState = { mode: 'single', stake: '10.00', picks: [] }
const listeners = new Set<() => void>()
let state: SlipState = EMPTY
let loaded = false

function parse(raw: string | null): SlipState {
  try {
    const data = raw ? JSON.parse(raw) : null
    if (!data || !Array.isArray(data.picks)) return EMPTY
    return {
      mode: data.mode === 'express' ? 'express' : 'single',
      stake: typeof data.stake === 'string' ? data.stake : EMPTY.stake,
      picks: data.picks.filter((pick: SlipPick) => typeof pick?.selection === 'number'),
    }
  } catch {
    return EMPTY
  }
}

function load() {
  if (loaded) return
  loaded = true
  try {
    state = parse(localStorage.getItem(SLIP_STORAGE_KEY))
  } catch {
    // private window or blocked storage: the slip lives in memory only
  }
}

function emit() {
  listeners.forEach((listener) => listener())
}

function set(next: SlipState) {
  state = next
  try {
    localStorage.setItem(SLIP_STORAGE_KEY, JSON.stringify(next))
  } catch {
    // the slip still works for this tab
  }
  emit()
}

function onStorage(event: StorageEvent) {
  if (event.key !== SLIP_STORAGE_KEY) return
  state = parse(event.newValue)
  emit()
}

// useSyncExternalStore: the server and the first client render see an empty slip, so the page
// hydrates cleanly; then the stored slip appears. Another tab's changes arrive by `storage`.
export function subscribe(listener: () => void) {
  listeners.add(listener)
  if (listeners.size === 1) window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) window.removeEventListener('storage', onStorage)
  }
}

export function getSnapshot() {
  load()
  return state
}

export function getServerSnapshot() {
  return EMPTY
}

export const slip = {
  // A pick leaves when tapped again. In an express a match has one pick: a second replaces the first.
  toggle(pick: SlipPick) {
    load()
    if (state.picks.some((item) => item.selection === pick.selection)) {
      set({ ...state, picks: state.picks.filter((item) => item.selection !== pick.selection) })
      return false
    }
    const keep = state.mode === 'express' ? state.picks.filter((item) => item.matchId !== pick.matchId) : state.picks
    set({ ...state, picks: [...keep, pick] })
    return true
  },
  remove(selection: number) {
    load()
    set({ ...state, picks: state.picks.filter((item) => item.selection !== selection) })
  },
  clear() {
    load()
    set({ ...state, picks: [] })
  },
  setMode(mode: SlipMode) {
    load()
    if (mode === 'express') {
      // one pick per match: the newest wins
      const seen = new Set<number>()
      const picks = [...state.picks].reverse().filter((pick) => !seen.has(pick.matchId) && seen.add(pick.matchId))
      set({ ...state, mode, picks: picks.reverse() })
    } else {
      set({ ...state, mode })
    }
  },
  setStake(stake: string) {
    load()
    set({ ...state, stake })
  },
  // The player accepted the new odds: the slip now holds what they see.
  acceptOdds(odds: Record<number, string>) {
    load()
    set({ ...state, picks: state.picks.map((pick) => ({ ...pick, odds: odds[pick.selection] ?? pick.odds })) })
  },
}
