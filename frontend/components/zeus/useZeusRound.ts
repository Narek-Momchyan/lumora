'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import {
  BIG_WIN_PAY,
  BONUS_END_MS,
  FIRST_GRID,
  GAME_SLUG,
  LIGHTNING_MS,
  SCATTER_SOUND_DELAY_MS,
  SHAKE_MS,
  SPEEDS,
  SPIN_COOLDOWN_MS,
  payToLc,
  teaserDelay,
} from '@/lib/zeus'
import type { SlotRoundSpin, SlotSoundPlayer, SlotSpinResponse, SpeedMode, ZeusOverlay } from '@/types/zeus'

// Lets one lightning end before the next one starts.
const BETWEEN_STRIKES_MS = 60

// Every kind of overlay without the id, which `showOverlay` adds.
type NewOverlay = ZeusOverlay extends infer Overlay ? (Overlay extends ZeusOverlay ? Omit<Overlay, 'id'> : never) : never

interface RoundOptions {
  sounds: SlotSoundPlayer
  speed: SpeedMode
  autoplay: boolean
  fallbackError: string
  onPools: (pools: Record<string, string>) => void
  onBalance: (balance: string) => void
}

function pause(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// Plays a round the backend has already settled. Nothing here decides a result: every grid,
// win and multiplier comes from the response, this hook only shows them one after another.
export default function useZeusRound({ sounds, speed, autoplay, fallbackError, onPools, onBalance }: RoundOptions) {
  const router = useRouter()
  const [grid, setGrid] = useState<string[][] | null>(FIRST_GRID)
  const [gridId, setGridId] = useState(0)
  const [winningCells, setWinningCells] = useState<[number, number][]>([])
  const [teaser, setTeaser] = useState(false)
  const [tumble, setTumble] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [awaitingSpin, setAwaitingSpin] = useState(false)
  const [inBonus, setInBonus] = useState(false)
  const [freeSpinsLeft, setFreeSpinsLeft] = useState(0)
  const [collected, setCollected] = useState<number[]>([])
  const [multiplier, setMultiplier] = useState(0)
  const [roundPay, setRoundPay] = useState(0)
  const [lastPayout, setLastPayout] = useState<string | null>(null)
  const [overlay, setOverlay] = useState<ZeusOverlay | null>(null)
  const [lightning, setLightning] = useState(false)
  const [shake, setShake] = useState(false)
  const [particles, setParticles] = useState(0)
  const [error, setError] = useState('')

  const busy = useRef(false)
  const skipping = useRef(false)
  const resultShown = useRef(false)
  const lastRoundEnd = useRef(0)
  const themePlaying = useRef(false)
  const overlayCount = useRef(0)
  const closeOverlayRef = useRef<() => void>(() => {})
  const pressSpinRef = useRef<() => void>(() => {})
  const autoplayRef = useRef(autoplay)

  useEffect(() => {
    autoplayRef.current = autoplay
  })

  async function wait(ms: number) {
    const end = Date.now() + ms
    while (Date.now() < end && !skipping.current) await pause(Math.min(50, ms))
  }

  function showOverlay(next: NewOverlay) {
    return new Promise<void>((resolve) => {
      closeOverlayRef.current = () => {
        setOverlay(null)
        resolve()
      }
      overlayCount.current += 1
      setOverlay({ ...next, id: overlayCount.current })
    })
  }

  function showGrid(next: string[][]) {
    setGrid(next)
    setGridId((id) => id + 1)
    if (next.flat().includes('scatter')) setTimeout(() => sounds.play('scatter_impact'), SCATTER_SOUND_DELAY_MS)
  }

  function showWin(cells: [number, number][]) {
    setWinningCells(cells)
    setTeaser(false)
    sounds.play('symbol_explode')
    sounds.play('sparkle_win')
    setShake(true)
    setTimeout(() => setShake(false), SHAKE_MS)
  }

  async function strikeMultipliers(values: number[]) {
    const { overlay: scale } = SPEEDS[speed]
    for (const value of values) {
      sounds.play('lightning_hit')
      sounds.play('collect_multiplier')
      setLightning(true)
      setCollected((list) => [...list, value])
      setMultiplier((total) => total + value)
      await wait(LIGHTNING_MS * scale)
      setLightning(false)
      await wait(BETWEEN_STRIKES_MS)
    }
  }

  async function playSpin(spin: SlotRoundSpin, paidBefore: number, response: SlotSpinResponse) {
    const timing = SPEEDS[speed]
    const [first] = spin.steps
    const teases = speed === 'normal' && !response.bonus_buy && !spin.is_free_spin

    skipping.current = false
    setTumble(0)
    setWinningCells([])
    setTeaser(teases)
    showGrid(first.grid)
    resultShown.current = true
    await wait(timing.land + (teases ? teaserDelay(first.grid) : 0))

    for (const [index, step] of spin.steps.entries()) {
      if (step.winning_cells.length === 0) continue

      setTumble(index + 1)
      showWin(step.winning_cells)
      setRoundPay(paidBefore + step.running_win)
      await wait(timing.win)

      setWinningCells([])
      const next = spin.steps[index + 1]
      if (next) showGrid(next.grid)
      await wait(timing.cascade)
    }

    await strikeMultipliers(spin.collected_multipliers)
    setMultiplier(spin.global_multiplier)
    setRoundPay(paidBefore + spin.win)
    await wait(spin.win > 0 ? timing.win : timing.end) // the win stays on screen before anything else starts
    setFreeSpinsLeft(spin.free_spins_left)

    if (spin.win >= BIG_WIN_PAY) {
      await showOverlay({ kind: 'big_win', payout: payToLc(spin.win, response.amount), amount: response.amount })
    }

    if (spin.free_spins_awarded > 0) {
      setInBonus(true)
      if (!themePlaying.current) sounds.play('free_spins_theme', true)
      themePlaying.current = true
      await showOverlay({ kind: 'bonus', count: spin.free_spins_awarded })
    }
  }

  // The backend has settled the whole round, but the player starts each free spin, like in the
  // original game. Autoplay goes on by itself.
  async function waitForSpinPress() {
    if (autoplayRef.current) {
      await pause(SPEEDS[speed].next)
      return
    }

    lastRoundEnd.current = Date.now()
    setAwaitingSpin(true)
    await new Promise<void>((resolve) => {
      pressSpinRef.current = resolve
    })
    setAwaitingSpin(false)
  }

  function endBonus() {
    setInBonus(false)
    sounds.stop('free_spins_theme')
    themePlaying.current = false
  }

  async function playRound(response: SlotSpinResponse) {
    let paid = 0
    for (const spin of response.result.spins) {
      if (spin.is_free_spin) await waitForSpinPress()
      await playSpin(spin, paid, response)
      paid += spin.win
    }

    setMultiplier(0)
    setLastPayout(response.payout)
    onPools(response.jackpot_pools)
    onBalance(response.balance)
    router.refresh() // the balance in the header and the history come from the server

    if (response.free_spins_played > 0) {
      await wait(BONUS_END_MS * SPEEDS[speed].overlay)
      endBonus()
      await showOverlay({ kind: 'summary', payout: response.payout })
    } else if (Number(response.payout) > 0 && paid < BIG_WIN_PAY) {
      setParticles(Date.now())
    }

    if (response.jackpot_tier) {
      await showOverlay({ kind: 'jackpot', tier: response.jackpot_tier, amount: response.jackpot_win })
    }
  }

  // Returns false when the round couldn't be played, so autoplay knows to stop.
  async function spin(amount: string, { bonusBuy = false, manual = false } = {}) {
    if (busy.current) return false
    if (manual && Date.now() - lastRoundEnd.current < SPIN_COOLDOWN_MS) return false

    busy.current = true
    skipping.current = false
    resultShown.current = false
    setIsPlaying(true)
    setError('')
    setRoundPay(0)
    setCollected([])
    setMultiplier(0)
    setParticles(0)
    setTeaser(false)
    setTumble(0)
    setGrid(null)

    try {
      const response = await apiFetch<SlotSpinResponse>('/slot_spins', {
        method: 'POST',
        body: { game: GAME_SLUG, amount, bonus_buy: bonusBuy },
      })
      await playRound(response)
      return true
    } catch (exception) {
      if (!(exception instanceof ApiError)) throw exception
      setGrid(FIRST_GRID)
      setError(errorDetail(exception, fallbackError))
      return false
    } finally {
      busy.current = false
      resultShown.current = false
      lastRoundEnd.current = Date.now()
      setIsPlaying(false)
    }
  }

  return {
    grid,
    gridId,
    winningCells,
    teaser,
    tumble,
    isPlaying,
    awaitingSpin,
    inBonus,
    freeSpinsLeft,
    collected,
    multiplier,
    roundPay,
    lastPayout,
    overlay,
    lightning,
    shake,
    particles,
    error,
    spin,
    // A click before the result is on screen must not skip the whole round.
    skip: () => {
      if (resultShown.current) skipping.current = true
    },
    closeOverlay: () => closeOverlayRef.current(),
    startFreeSpin: () => {
      if (Date.now() - lastRoundEnd.current >= SPIN_COOLDOWN_MS) pressSpinRef.current()
    },
  }
}
