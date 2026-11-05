'use client'

import { useRouter } from 'next/navigation'
import { createContext, use, useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ReactNode } from 'react'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { getOddsSnapshot, getServerOdds, putMarkets, putOdds, subscribeOdds } from '@/lib/odds-store'
import type { LiveOdds } from '@/lib/odds-store'
import { getServerSnapshot, getSnapshot, slip, subscribe } from '@/lib/slip-store'
import { POLL_SECONDS } from '@/lib/sports'
import type { Bet, BetLabels, Market, SportsUiLabels } from '@/types/sports'
import SlipFlights from './SlipFlights'
import type { Flight } from './SlipFlights'

type Status = 'idle' | 'placing' | 'placed'

interface SlipContextValue {
  ui: SportsUiLabels
  bet: BetLabels
  balance: string | null
  currency: string
  status: Status
  error: string
  note: string // "the odds changed" after a 409
  place: () => Promise<void>
  fly: (from: DOMRect) => void
  watch: (query: string) => () => void
}

const SlipContext = createContext<SlipContextValue | null>(null)

interface SlipProviderProps {
  ui: SportsUiLabels | null
  bet: BetLabels | null
  balance: string | null
  currency: string
  children: ReactNode
}

// The bet slip's brain, mounted once in the site layout so it is the same on every page: placing
// bets, polling the odds of what the slip and the page show, and the "flying pick" animation.
export default function SlipProvider({ ui, bet, balance, currency, children }: SlipProviderProps) {
  const router = useRouter()
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState('')
  const [note, setNote] = useState('')
  const [flights, setFlights] = useState<Flight[]>([])
  const watchers = useRef(new Map<string, number>())
  const nextFlight = useRef(0)

  const poll = useCallback(async (only?: string) => {
    if (document.hidden) return
    const queries = new Set(watchers.current.keys())
    const ids = [...new Set(getSnapshot().picks.map((pick) => pick.matchId))]
    if (ids.length > 0) queries.add(`match=${ids.join(',')}`)
    for (const query of only ? [only] : queries) {
      try {
        putMarkets(await apiFetch<Market[]>(`/markets?${query}`, { auth: false }))
      } catch {
        // the next poll tries again; the prices on screen stay as they were
      }
    }
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => poll(), POLL_SECONDS * 1000)
    const wake = () => poll()
    document.addEventListener('visibilitychange', wake)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', wake)
    }
  }, [poll])

  const watch = useCallback(
    (query: string) => {
      watchers.current.set(query, (watchers.current.get(query) ?? 0) + 1)
      poll(query)
      return () => {
        const count = (watchers.current.get(query) ?? 1) - 1
        if (count <= 0) watchers.current.delete(query)
        else watchers.current.set(query, count)
      }
    },
    [poll],
  )

  const fly = useCallback((from: DOMRect) => {
    nextFlight.current += 1
    setFlights((rows) => [
      ...rows,
      { id: nextFlight.current, x: from.left + from.width / 2, y: from.top + from.height / 2 },
    ])
  }, [])

  const place = useCallback(async () => {
    const state = getSnapshot()
    setStatus('placing')
    setError('')
    setNote('')

    // Single: every pick is its own bet with this stake. Express: one bet with all the picks.
    const bets = state.mode === 'single' ? state.picks.map((pick) => [pick]) : [state.picks]
    try {
      for (const picks of bets) {
        await apiFetch<Bet & { balance: string }>('/sport_bets', {
          method: 'POST',
          body: {
            key: crypto.randomUUID(),
            stake: state.stake,
            selections: picks.map((pick) => ({ selection: pick.selection, odds: pick.odds })),
          },
        })
        for (const pick of picks) slip.remove(pick.selection) // placed: it leaves the slip
      }
      setStatus('placed')
      router.refresh() // the balance in the header comes from the server
      window.setTimeout(() => setStatus('idle'), 2500)
    } catch (exception) {
      setStatus('idle')
      if (!(exception instanceof ApiError)) throw exception
      const data = exception.data as { code?: string; selections?: { selection: number; odds: string }[] } | null
      if (exception.status === 409 && data?.code === 'odds_changed' && data.selections) {
        putOdds(data.selections) // the slip shows the new prices and asks to confirm
        setNote(ui?.odds_changed_note ?? '')
      } else {
        setError(errorDetail(exception, ui?.server_unreachable ?? ''))
      }
    }
  }, [router, ui])

  if (!ui || !bet) return children

  return (
    <SlipContext value={{ ui, bet, balance, currency, status, error, note, place, fly, watch }}>
      {children}
      <SlipFlights flights={flights} onDone={(id) => setFlights((rows) => rows.filter((row) => row.id !== id))} />
    </SlipContext>
  )
}

export function useSlipContext() {
  return use(SlipContext)
}

export function useSlip() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}

export function useOddsMap() {
  return useSyncExternalStore(subscribeOdds, getOddsSnapshot, getServerOdds)
}

// Watch a set of markets on this page (?match=1,2 or ?date=2026-11-08&kind=1x2) while it is open.
export function useWatchOdds(query: string) {
  const context = useSlipContext()
  const watch = context?.watch
  useEffect(() => (watch ? watch(query) : undefined), [watch, query])
}

export type { LiveOdds }
