'use client'

import { useEffect, useRef, useState } from 'react'
import OddsButton from '@/components/ui/OddsButton'
import useNow from '@/lib/useNow'
import { slip } from '@/lib/slip-store'
import { hasStarted, trend } from '@/lib/sports'
import type { Market, Match, Selection } from '@/types/sports'
import { useOddsMap, useSlip, useSlipContext } from './SlipProvider'

interface OddsCellProps {
  selection: Pick<Selection, 'id' | 'odds' | 'previous_odds'>
  match: Pick<Match, 'id' | 'kickoff' | 'status' | 'home' | 'away'>
  kind: Market['kind']
  line: string | null
  code: string
  label?: string
  stacked?: boolean
  marketOpen?: boolean
}

// An odds button wired to the bet slip: it shows the newest price (▲ / ▼, a 2-second flash when it
// moves), is lit while its pick is in the slip, and closes at kickoff.
export default function OddsCell({ selection, match, kind, line, code, label, stacked, marketOpen = true }: OddsCellProps) {
  const slipContext = useSlipContext()
  const live = useOddsMap().get(selection.id)
  const picks = useSlip().picks
  const now = useNow(5000)
  const box = useRef<HTMLDivElement>(null)

  const odds = live?.odds ?? selection.odds
  const previous = live ? live.previous : selection.previous_odds
  const open = (live?.open ?? marketOpen) && !hasStarted(match, now)
  const selected = picks.some((pick) => pick.selection === selection.id)

  // The price changed while the page was open: flash it for 2 seconds.
  const [shown, setShown] = useState(odds)
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  if (odds !== shown) {
    setShown(odds)
    setFlash(Number(odds) > Number(shown) ? 'up' : 'down')
  }
  useEffect(() => {
    if (!flash) return
    const timer = window.setTimeout(() => setFlash(null), 2000)
    return () => window.clearTimeout(timer)
  }, [flash])

  function choose() {
    const added = slip.toggle({
      selection: selection.id,
      matchId: match.id,
      kickoff: match.kickoff,
      kind,
      line,
      code,
      odds,
      home: match.home.short_name || match.home.name,
      away: match.away.short_name || match.away.name,
    })
    if (added && box.current && !document.hidden) slipContext?.fly(box.current.getBoundingClientRect())
  }

  return (
    <div ref={box} className="min-w-0">
      <OddsButton
        label={label}
        stacked={stacked}
        odds={odds}
        trend={trend(odds, previous)}
        flash={flash}
        selected={selected}
        disabled={!open}
        onClick={choose}
      />
    </div>
  )
}
