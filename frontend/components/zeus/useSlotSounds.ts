'use client'

import { useEffect, useRef, useSyncExternalStore } from 'react'
import type { SlotSound } from '@/types/zeus'

const MUTE_KEY = 'lumora.zeus.muted'
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
export default function useSlotSounds(sounds: SlotSound[]) {
  const muted = useSyncExternalStore(subscribe, readMuted, () => false)
  const audios = useRef(new Map<string, HTMLAudioElement>())
  const mutedRef = useRef(muted)

  useEffect(() => {
    mutedRef.current = muted
    if (muted) audios.current.forEach((audio) => audio.pause())
  }, [muted])

  useEffect(() => {
    const loaded = audios.current
    sounds.forEach(({ code, file }) => loaded.set(code, Object.assign(new Audio(file), { preload: 'auto' })))
    return () => {
      loaded.forEach((audio) => audio.pause())
      loaded.clear()
    }
  }, [sounds])

  function play(code: string, loop = false) {
    const audio = audios.current.get(code)
    if (!audio || mutedRef.current) return
    audio.loop = loop
    audio.currentTime = 0
    audio.play().catch(() => {}) // the browser can refuse before the first click
  }

  function stop(code: string) {
    audios.current.get(code)?.pause()
  }

  return { muted, toggleMuted: () => saveMuted(!muted), play, stop }
}
