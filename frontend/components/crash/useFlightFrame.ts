'use client'

import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'
import { flightMs } from '@/lib/crash'
import type { CrashRound } from '@/types/crash'

// Runs on every animation frame with the milliseconds of the flight, by the server's clock.
// It writes to the DOM directly: a React render on every frame would be far too slow.
export default function useFlightFrame(
  round: CrashRound | null,
  clockOffset: RefObject<number | null>,
  onFrame: (flight: number, serverNow: number) => void,
) {
  const latest = useRef(onFrame)

  useEffect(() => {
    latest.current = onFrame
  })

  useEffect(() => {
    let frame: number

    function tick() {
      const serverNow = Date.now() + (clockOffset.current ?? 0)
      let flight = 0
      if (round?.crash_point) flight = flightMs(Number(round.crash_point))
      else if (round?.started_at) flight = serverNow - Date.parse(round.started_at)
      latest.current(flight, serverNow)
      frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [round, clockOffset])
}
