'use client'

import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { SlotSound } from '@/types/zeus'

const MUTE_KEY = 'lumora.zeus.muted'
const OVERLAP_GAP_MS = 35

// The same volumes as the original Zeus Legacy. Every other sound plays at full volume.
const SOUND_OPTIONS: Record<string, { volume?: number; rate?: number; overlap?: boolean }> = {
  stone_tumble: { volume: 0.5, rate: 1.3, overlap: true },
  big_win: { volume: 0.8 },
  symbol_explode: { volume: 0.6 },
  win_tick: { volume: 0.5 },
}

const listeners = new Set<() => void>()

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function readMuted() {
  try {
    return localStorage.getItem(MUTE_KEY) === 'true'
  } catch {
    return false
  }
}

function saveMuted(muted: boolean) {
  try {
    localStorage.setItem(MUTE_KEY, String(muted))
  } catch {
    // A private window can refuse storage: the sound setting just isn't remembered.
  }
  listeners.forEach((listener) => listener())
}

// Only sounds uploaded in the admin exist. A code without a file simply plays nothing.
export default function useSlotSounds(initialSounds: SlotSound[]) {
  const muted = useSyncExternalStore(subscribe, readMuted, () => false)
  const audios = useRef(new Map<string, HTMLAudioElement>())
  const mutedRef = useRef(muted)
  const lastOverlap = useRef(0)
  // The refresh after a round brings a new list. Keeping the first one lets playing sounds finish.
  const [sounds] = useState(initialSounds)

  useEffect(() => {
    mutedRef.current = muted
    if (muted) audios.current.forEach((audio) => audio.pause())
  }, [muted])

  // Browsers refuse sound before the first click or key, so nothing loads until then.
  useEffect(() => {
    const loaded = audios.current

    function load() {
      window.removeEventListener('pointerdown', load)
      window.removeEventListener('keydown', load)
      sounds.forEach(({ code, file }) => loaded.set(code, Object.assign(new Audio(file), { preload: 'auto' })))
    }

    window.addEventListener('pointerdown', load)
    window.addEventListener('keydown', load)

    return () => {
      window.removeEventListener('pointerdown', load)
      window.removeEventListener('keydown', load)
      loaded.forEach((audio) => audio.pause())
      loaded.clear()
    }
  }, [sounds])

  function play(code: string, loop = false) {
    const cached = audios.current.get(code)
    if (!cached || mutedRef.current) return

    const { volume = 1, rate = 1, overlap = false } = SOUND_OPTIONS[code] ?? {}
    if (overlap && Date.now() - lastOverlap.current < OVERLAP_GAP_MS) return
    if (overlap) lastOverlap.current = Date.now()

    const audio = overlap ? (cached.cloneNode() as HTMLAudioElement) : cached
    audio.loop = loop
    audio.volume = volume
    audio.playbackRate = rate
    audio.currentTime = 0
    audio.play().catch(() => {}) // the browser can still refuse, and a missing sound must not stop the game
  }

  function stop(code: string) {
    audios.current.get(code)?.pause()
  }

  return { muted, toggleMuted: () => saveMuted(!muted), play, stop }
}
