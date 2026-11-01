'use client'

import type { RefObject } from 'react'
import { flightMs } from '@/lib/crash'
import useServerFrame from '@/lib/useServerFrame'
import type { CrashRound } from '@/types/crash'

// Runs on every animation frame with the milliseconds of the flight, by the server's clock.
// It writes to the DOM directly: a React render on every frame would be far too slow.
export default function useFlightFrame(
  round: CrashRound | null,
  clockOffset: RefObject<number | null>,
  onFrame: (flight: number, serverNow: number) => void,
) {
  useServerFrame(clockOffset, (serverNow) => {
    let flight = 0
    if (round?.crash_point) flight = flightMs(Number(round.crash_point))
    else if (round?.started_at) flight = serverNow - Date.parse(round.started_at)
    onFrame(flight, serverNow)
  })
}
