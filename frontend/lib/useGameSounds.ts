'use client'

import { useCallback, useEffect, useMemo, useRef, useSyncExternalStore } from 'react'
import type { GameSound, SoundCode } from '@/types/sound'

// The choice is remembered in this browser only (localStorage), not in a cookie: the server never needs it,
// so a cookie would only travel with every request. Both games share it. The default is MUTED.
const STORAGE_KEY = 'lumora.sound'
const DEFAULT_VOLUME = 0.8

// How loud each sound is next to the others, before the player's volume. The flight loop is a bed, not a hit.
const BASE_VOLUME: Partial<Record<SoundCode, number>> = { crash_flight: 0.5 }

interface Preference {
  muted: boolean
  volume: number
}

const listeners = new Set<() => void>()

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

// useSyncExternalStore wants a value that is the same until it really changes: the raw stored string is.
function readRaw() {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? ''
  } catch {
    return '' // a private window can refuse storage: the choice is just not remembered
  }
}

export function parsePreference(raw: string): Preference {
  try {
    const value = JSON.parse(raw) as Partial<Preference>
    const volume = typeof value.volume === 'number' ? Math.min(1, Math.max(0, value.volume)) : DEFAULT_VOLUME
    return { muted: value.muted !== false, volume } // anything but an explicit "unmuted" is muted
  } catch {
    return { muted: true, volume: DEFAULT_VOLUME }
  }
}

function save(next: Preference) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // not remembered; the session still follows the new choice through the listeners below
  }
  listeners.forEach((listener) => listener())
}

// The sounds of a game page. Only files uploaded in the admin exist; playing a key without one does nothing.
// Browsers refuse sound before a click, so nothing is created until the player turns the sound on: that click
// is the unlock. A loop (the flight) that was asked for while muted starts when the sound is turned on.
export default function useGameSounds(sounds: GameSound[]) {
  const raw = useSyncExternalStore(subscribe, readRaw, () => '')
  const { muted, volume } = useMemo(() => parsePreference(raw), [raw])
  const audios = useRef(new Map<string, HTMLAudioElement>())
  const loops = useRef(new Set<SoundCode>())
  const state = useRef({ muted, volume })

  const start = useCallback((code: SoundCode, loop: boolean) => {
    const audio = audios.current.get(code)
    if (!audio || state.current.muted) return
    audio.loop = loop
    audio.volume = (BASE_VOLUME[code] ?? 1) * state.current.volume
    audio.currentTime = 0
    audio.play().catch(() => {}) // the browser can still refuse, and a missing sound must not stop the game
  }, [])

  useEffect(() => {
    state.current = { muted, volume }
    audios.current.forEach((audio, code) => {
      audio.volume = (BASE_VOLUME[code as SoundCode] ?? 1) * volume
      if (muted) audio.pause()
    })
  }, [muted, volume])

  // Turning the sound on brings back a loop that is still wanted. Only the mute switch does this: moving the
  // volume slider must not restart the flight sound.
  useEffect(() => {
    if (!muted) loops.current.forEach((code) => start(code, true))
  }, [muted, start])

  // Create the audio elements only once the sound is on (the player clicked the button).
  useEffect(() => {
    if (muted) return
    for (const { code, file } of sounds) {
      if (!audios.current.has(code)) audios.current.set(code, Object.assign(new Audio(file), { preload: 'auto' }))
    }
  }, [muted, sounds])

  // A hidden tab is silent; a loop that is still wanted comes back with the tab.
  useEffect(() => {
    function onVisibility() {
      if (document.hidden) audios.current.forEach((audio) => audio.pause())
      else loops.current.forEach((code) => start(code, true))
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [start])

  useEffect(() => {
    const loaded = audios.current
    return () => loaded.forEach((audio) => audio.pause())
  }, [])

  const play = useCallback(
    (code: SoundCode, loop = false) => {
      if (loop) loops.current.add(code)
      start(code, loop)
    },
    [start],
  )

  const stop = useCallback((code: SoundCode) => {
    loops.current.delete(code)
    audios.current.get(code)?.pause()
  }, [])

  // The click that turns the sound on also "primes" every element once (a silent play), which Safari needs.
  const toggleMuted = useCallback(() => {
    const now = parsePreference(readRaw())
    if (now.muted) {
      for (const { code, file } of sounds) {
        if (!audios.current.has(code)) audios.current.set(code, Object.assign(new Audio(file), { preload: 'auto' }))
      }
      audios.current.forEach((audio) => {
        audio.muted = true
        audio.play().then(
          () => {
            audio.pause()
            audio.currentTime = 0
            audio.muted = false
          },
          () => {
            audio.muted = false
          },
        )
      })
    }
    save({ ...now, muted: !now.muted })
  }, [sounds])

  const setVolume = useCallback((next: number) => save({ ...parsePreference(readRaw()), volume: next }), [])

  return { muted, volume, play, stop, toggleMuted, setVolume }
}
