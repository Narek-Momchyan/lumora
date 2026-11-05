import type { Market } from '@/types/sports'

export interface LiveOdds {
  odds: string
  previous: string | null
  open: boolean
}

// The newest odds of every selection the page or the bet slip is watching (polled, see
// components/sports/SlipProvider). A page renders the odds it got from the server; when a newer
// price is here, that one wins and the cell flashes.
let live = new Map<number, LiveOdds>()
const listeners = new Set<() => void>()

export function subscribeOdds(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function getOddsSnapshot() {
  return live
}

const NOTHING = new Map<number, LiveOdds>()
export function getServerOdds() {
  return NOTHING
}

export function putMarkets(markets: Market[]) {
  const next = new Map(live)
  for (const market of markets) {
    for (const selection of market.selections) {
      next.set(selection.id, {
        odds: selection.odds,
        previous: selection.previous_odds,
        open: market.status === 'open',
      })
    }
  }
  live = next
  listeners.forEach((listener) => listener())
}

// A 409 odds_changed answers with the new prices of the selections that moved.
export function putOdds(changes: { selection: number; odds: string }[]) {
  const next = new Map(live)
  for (const { selection, odds } of changes) {
    const old = next.get(selection)
    next.set(selection, { odds, previous: old?.odds ?? null, open: old?.open ?? true })
  }
  live = next
  listeners.forEach((listener) => listener())
}
