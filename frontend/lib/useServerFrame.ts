'use client'

import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'

// Runs on every animation frame with the time by the server's clock.
export default function useServerFrame(clockOffset: RefObject<number | null>, onFrame: (serverNow: number) => void) {
  const latest = useRef(onFrame)

  useEffect(() => {
    latest.current = onFrame
  })

  useEffect(() => {
    let frame: number

    function tick() {
      latest.current(Date.now() + (clockOffset.current ?? 0))
      frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [clockOffset])
}
