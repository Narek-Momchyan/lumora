'use client'

import { useCallback, useEffect, useMemo, useRef, useSyncExternalStore } from 'react'
import type { GameSound, SoundCode } from '@/types/sound'

// The choice is remembered in this browser only (localStorage), not in a cookie: the server never needs it,
// so a cookie would only travel with every request. Both games share it. The default is MUTED.
const STORAGE_KEY = 'lumora.sound'
const DEFAULT_VOLUME = 0.8

// How loud each sound is next to the others, before the player's volume. The flight loop is a bed, not a hit.
const BASE_VOLUME: Partial<Record<SoundCode, number>> = { crash_flight: 0.5 }

// A loop plays through the Web Audio API: an <audio loop> leaves a short gap at the end of every pass, which
// is plain to hear in a long flight. A buffer source loops without one.
const LOOPS = new Set<SoundCode>(['crash_flight'])

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
  const audios = useRef(new Map<string, HTMLAudioElement>()) // the one-shot sounds
  const context = useRef<AudioContext | null>(null) // the loops
  const buffers = useRef(new Map<string, AudioBuffer>())
  const running = useRef(new Map<SoundCode, { source: AudioBufferSourceNode; gain: GainNode }>())
  const loops = useRef(new Set<SoundCode>()) // loops that are wanted now, whether or not they can sound yet
  const state = useRef({ muted, volume })

  const startOnce = useCallback((code: SoundCode) => {
    const audio = audios.current.get(code)
    if (!audio || state.current.muted) return
    audio.volume = (BASE_VOLUME[code] ?? 1) * state.current.volume
    audio.currentTime = 0
    audio.play().catch(() => {}) // the browser can still refuse, and a missing sound must not stop the game
  }, [])

  const halt = useCallback((code: SoundCode) => {
    const run = running.current.get(code)
    if (!run) return
    running.current.delete(code)
    try {
      run.source.stop()
    } catch {
      // already stopped
    }
    run.source.disconnect()
  }, [])

  const startLoop = useCallback((code: SoundCode) => {
    const ctx = context.current
    const buffer = buffers.current.get(code)
    if (!ctx || !buffer || state.current.muted || running.current.has(code)) return
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.loop = true
    const gain = ctx.createGain()
    gain.gain.value = (BASE_VOLUME[code] ?? 1) * state.current.volume
    source.connect(gain).connect(ctx.destination)
    source.start()
    running.current.set(code, { source, gain })
  }, [])

  useEffect(() => {
    state.current = { muted, volume }
    audios.current.forEach((audio, code) => {
      audio.volume = (BASE_VOLUME[code as SoundCode] ?? 1) * volume
      if (muted) audio.pause()
    })
    running.current.forEach(({ gain }, code) => {
      gain.gain.value = (BASE_VOLUME[code] ?? 1) * volume
    })
    if (muted) [...running.current.keys()].forEach(halt)
  }, [muted, volume, halt])

  // Load the files only once the sound is on (the player clicked the button): the one-shots as audio elements,
  // the loops decoded into buffers. A loop that was asked for while it loaded starts when it is ready.
  useEffect(() => {
    if (muted) return
    let cancelled = false
    for (const { code, file } of sounds) {
      if (LOOPS.has(code as SoundCode)) {
        context.current ??= new AudioContext()
        if (buffers.current.has(code)) continue
        fetch(file)
          .then((response) => response.arrayBuffer())
          .then((data) => context.current!.decodeAudioData(data))
          .then((buffer) => {
            if (cancelled) return
            buffers.current.set(code, buffer)
            if (loops.current.has(code as SoundCode)) startLoop(code as SoundCode)
          })
          .catch(() => {}) // a file that does not load is just a missing sound
      } else if (!audios.current.has(code)) {
        audios.current.set(code, Object.assign(new Audio(file), { preload: 'auto' }))
      }
    }
    return () => {
      cancelled = true
    }
  }, [muted, sounds, startLoop])

  // Turning the sound on brings back a loop that is still wanted. Only the mute switch does this: moving the
  // volume slider must not restart the flight sound.
  useEffect(() => {
    if (!muted) loops.current.forEach(startLoop)
  }, [muted, startLoop])

  // A hidden tab is silent; a loop that is still wanted comes back with the tab. A page that was opened with
  // the sound already on needs one click before the browser lets the loops sound: resume then.
  useEffect(() => {
    function onVisibility() {
      if (document.hidden) {
        audios.current.forEach((audio) => audio.pause())
        ;[...running.current.keys()].forEach(halt)
      } else {
        loops.current.forEach(startLoop)
      }
    }
    function resume() {
      context.current?.resume().then(() => loops.current.forEach(startLoop), () => {})
    }
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('pointerdown', resume)
    window.addEventListener('keydown', resume)
    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('pointerdown', resume)
      window.removeEventListener('keydown', resume)
    }
  }, [halt, startLoop])

  useEffect(() => {
    const loaded = audios.current
    const playingNow = running.current
    return () => {
      loaded.forEach((audio) => audio.pause())
      ;[...playingNow.keys()].forEach(halt)
    }
  }, [halt])

  const play = useCallback(
    (code: SoundCode, loop = false) => {
      if (loop && LOOPS.has(code)) {
        loops.current.add(code)
        startLoop(code)
      } else {
        startOnce(code)
      }
    },
    [startLoop, startOnce],
  )

  const stop = useCallback(
    (code: SoundCode) => {
      loops.current.delete(code)
      halt(code)
      audios.current.get(code)?.pause()
    },
    [halt],
  )

  // The click that turns the sound on is the unlock: it creates and resumes the audio context and "primes" every
  // audio element once with a silent play, which Safari needs.
  const toggleMuted = useCallback(() => {
    const now = parsePreference(readRaw())
    if (now.muted) {
      context.current ??= new AudioContext()
      context.current.resume().catch(() => {})
      for (const { code, file } of sounds) {
        if (!LOOPS.has(code as SoundCode) && !audios.current.has(code)) {
          audios.current.set(code, Object.assign(new Audio(file), { preload: 'auto' }))
        }
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
