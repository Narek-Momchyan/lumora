'use client'

import { useEffect } from 'react'

// The sports background lives in globals.css (.sports-backdrop); only the sports theme shows it.
// Here: a hidden tab pauses its animation, so it costs nothing in the background.
export default function SportsBackdrop() {
  useEffect(() => {
    function sync() {
      document.documentElement.toggleAttribute('data-paused', document.hidden)
    }
    sync()
    document.addEventListener('visibilitychange', sync)
    return () => document.removeEventListener('visibilitychange', sync)
  }, [])

  return (
    <div className="sports-backdrop" aria-hidden="true">
      <div className="sports-backdrop-stripes" />
      <div className="sports-backdrop-glow" />
      <div className="sports-backdrop-glow" />
    </div>
  )
}
