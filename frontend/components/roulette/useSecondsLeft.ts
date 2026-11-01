'use client'

import { useState } from 'react'
import type { RefObject } from 'react'
import useServerFrame from '@/lib/useServerFrame'

// Whole seconds until a moment, by the server's clock. It renders only when the number changes.
export default function useSecondsLeft(deadline: number | null, clockOffset: RefObject<number | null>) {
  const [seconds, setSeconds] = useState(0)

  useServerFrame(clockOffset, (serverNow) => {
    setSeconds(deadline === null ? 0 : Math.max(0, Math.ceil((deadline - serverNow) / 1000)))
  })

  return seconds
}
