'use client'

import { useEffect, useState } from 'react'

// The current time in milliseconds, renewed every `everyMs` (and not while the tab is hidden).
export default function useNow(everyMs = 1000) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!document.hidden) setNow(Date.now())
    }, everyMs)
    return () => window.clearInterval(timer)
  }, [everyMs])

  return now
}
