'use client'

import { useRouter } from 'next/navigation'
import { useRef, useState } from 'react'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { GAME_SLUG, SPEEDS, winStage } from '@/lib/zeus'
import type { SlotRoundSpin, SlotSpinResponse, SpeedMode, ZeusOverlay } from '@/types/zeus'

interface Sounds {
  play: (code: string, loop?: boolean) => void
  stop: (code: string) => void
}

interface RoundOptions {
  sounds: Sounds
  speed: SpeedMode
  fallbackError: string
  onPools: (pools: Record<string, string>) => void
  onBalance: (balance: string) => void
}

function pause(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// Plays a round the backend has already settled. Nothing here decides a result: every grid,
// win and multiplier comes from the response, this hook only shows them one after another.
export default function useZeusRound({ sounds, speed, fallbackError, onPools, onBalance }: RoundOptions) {
  const router = useRouter()
  const [grid, setGrid] = useState<string[][] | null>(null)
  const [spinNumber, setSpinNumber] = useState(0)
  const [winningCells, setWinningCells] = useState<[number, number][]>([])
  const [tumble, setTumble] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [inBonus, setInBonus] = useState(false)
  const [freeSpinsLeft, setFreeSpinsLeft] = useState(0)
  const [collected, setCollected] = useState<number[]>([])
  const [multiplier, setMultiplier] = useState(0)
  const [roundPay, setRoundPay] = useState(0)
  const [lastPayout, setLastPayout] = useState<string | null>(null)
  const [overlay, setOverlay] = useState<ZeusOverlay | null>(null)
  const [lightning, setLightning] = useState(false)
  const [shake, setShake] = useState(false)
  const [error, setError] = useState('')

  const busy = useRef(false)
  const skipping = useRef(false)
  const closeOverlayRef = useRef<() => void>(() => {})

  async function wait(ms: number) {
    const end = Date.now() + ms
    while (Date.now() < end && !skipping.current) await pause(Math.min(50, ms))
  }

  function showOverlay(next: ZeusOverlay) {
    return new Promise<void>((resolve) => {
      closeOverlayRef.current = () => {
        setOverlay(null)
        resolve()
      }
      setOverlay(next)
    })
  }

  async function playSpin(spin: SlotRoundSpin, paidBefore: number) {
    const timing = SPEEDS[speed]
    setSpinNumber((number) => number + 1)
    setTumble(0)
    setWinningCells([])
    if (!spin.is_free_spin) setCollected([])

    for (const [index, step] of spin.steps.entries()) {
      setGrid(step.grid)
      if (index > 0) sounds.play('stone_tumble')
      if (step.grid.flat().includes('scatter')) sounds.play('scatter_impact')
      await wait(index === 0 ? timing.land : timing.cascade)
      setRoundPay(paidBefore + step.running_win)
      if (step.winning_cells.length === 0) continue

      setTumble(index + 1)
      setWinningCells(step.winning_cells)
      setShake(true)
      sounds.play('symbol_explode')
      sounds.play('sparkle_win')
      await wait(timing.win)
      setShake(false)
      setWinningCells([])
    }

    if (spin.collected_multipliers.length > 0) {
      setCollected((list) => [...list, ...spin.collected_multipliers])
      setLightning(true)
      sounds.play('lightning_hit')
      sounds.play('collect_multiplier')
      await wait(timing.win)
      setLightning(false)
    }
    setMultiplier(spin.global_multiplier)
    setRoundPay(paidBefore + spin.win)
    setFreeSpinsLeft(spin.free_spins_left)

    if (spin.free_spins_awarded > 0) {
      setInBonus(true)
      sounds.play('free_spins_theme', true)
      if (!skipping.current) await showOverlay({ kind: 'bonus', count: spin.free_spins_awarded })
    }
    await wait(timing.end)
  }

  async function playRound(response: SlotSpinResponse) {
    let paid = 0
    for (const spin of response.result.spins) {
      await playSpin(spin, paid)
      paid += spin.win
    }

    setInBonus(false)
    setMultiplier(0)
    sounds.stop('free_spins_theme')
    setLastPayout(response.payout)
    onPools(response.jackpot_pools)
    onBalance(response.balance)
    router.refresh() // the balance in the header and the history come from the server

    const stage = winStage(response.payout, response.amount)
    if (response.free_spins_played > 0) await showOverlay({ kind: 'summary', payout: response.payout })
    else if (stage) {
      sounds.play('epic_drop')
      sounds.play(stage === 'win_big' ? 'big_win' : stage === 'win_ultra' || stage === 'win_max' ? 'ultra_win' : 'mega_win')
      await showOverlay({ kind: 'big_win', payout: response.payout, stage })
    }
    if (response.jackpot_tier) {
      await showOverlay({ kind: 'jackpot', tier: response.jackpot_tier, amount: response.jackpot_win })
    }
  }

  // Returns false when the round couldn't be played, so autoplay knows to stop.
  async function spin(amount: string, bonusBuy = false) {
    if (busy.current) return false
    busy.current = true
    skipping.current = false
    setIsPlaying(true)
    setError('')
    setRoundPay(0)
    setCollected([])

    try {
      const response = await apiFetch<SlotSpinResponse>('/slot_spins', {
        method: 'POST',
        body: { game: GAME_SLUG, amount, bonus_buy: bonusBuy },
      })
      await playRound(response)
      return true
    } catch (exception) {
      if (!(exception instanceof ApiError)) throw exception
      setError(errorDetail(exception, fallbackError))
      return false
    } finally {
      busy.current = false
      setIsPlaying(false)
    }
  }

  return {
    grid,
    spinNumber,
    winningCells,
    tumble,
    isPlaying,
    inBonus,
    freeSpinsLeft,
    collected,
    multiplier,
    roundPay,
    lastPayout,
    overlay,
    lightning,
    shake,
    error,
    spin,
    skip: () => {
      skipping.current = true
    },
    closeOverlay: () => closeOverlayRef.current(),
  }
}
