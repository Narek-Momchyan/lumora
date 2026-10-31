'use client'

import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { formatCount } from '@/lib/zeus'
import type { SlotSoundPlayer, ZeusPageLabels } from '@/types/zeus'
import { makeBigWinCoins } from './effects'

const COUNT_MS = 6000
const HOLD_MS = 3000
const TICK_MS = 150
const COINS = 65

const STAGES = [
  { label: 'win_winning', times: 0, color: 'var(--color-zeus-blue)' },
  { label: 'win_big', times: 10, color: 'var(--color-zeus-gold)' },
  { label: 'win_super', times: 25, color: 'var(--color-zeus-orange)' },
  { label: 'win_mega', times: 50, color: 'var(--color-zeus-red)' },
  { label: 'win_ultra', times: 100, color: 'var(--color-zeus-purple)' },
  { label: 'win_max', times: 200, color: 'var(--color-zeus-yellow)' },
] as const

function stageOf(times: number) {
  return STAGES.findLastIndex((stage) => times >= stage.times)
}

function fanfare(stage: number) {
  if (stage === 1) return 'big_win'
  if (stage === 2 || stage === 3) return 'mega_win'
  return 'ultra_win'
}

interface BigWinOverlayProps {
  payout: string
  amount: string
  currency: string
  labels: ZeusPageLabels
  scale: number
  sounds: SlotSoundPlayer
  onClose: () => void
}

export default function BigWinOverlay({ payout, amount, currency, labels, scale, sounds, onClose }: BigWinOverlayProps) {
  const [shown, setShown] = useState(0)
  const [stage, setStage] = useState(0)
  const [shake, setShake] = useState(0)
  const [counting, setCounting] = useState(true)
  const [coins] = useState(() => makeBigWinCoins(COINS))
  const latest = useRef({ sounds, onClose })
  const current = STAGES[stage]

  useEffect(() => {
    latest.current = { sounds, onClose }
  })

  useEffect(() => {
    latest.current.sounds.play('epic_drop')
  }, [])

  useEffect(() => {
    if (!counting) return
    const ticks = setInterval(() => latest.current.sounds.play('win_tick'), TICK_MS)
    return () => clearInterval(ticks)
  }, [counting])

  useEffect(() => {
    const end = Number(payout)
    const bet = Number(amount)
    const duration = COUNT_MS * scale
    const start = performance.now()
    let lastStage = 0
    let frame = 0
    let closeTimer: ReturnType<typeof setTimeout>

    function update(now: number) {
      // The first frame's time can be a moment before `start`.
      const progress = Math.min(Math.max(now - start, 0) / duration, 1)
      const value = (1 - Math.pow(1 - progress, 3)) * end
      const nextStage = stageOf(value / bet)
      setShown(value)

      if (nextStage !== lastStage) {
        lastStage = nextStage
        setStage(nextStage)
        setShake(10 + nextStage * 10)
        setTimeout(() => setShake(0), 500)
        latest.current.sounds.play(fanfare(nextStage))
      }

      if (progress < 1) frame = requestAnimationFrame(update)
      else {
        setCounting(false)
        closeTimer = setTimeout(() => latest.current.onClose(), HOLD_MS * scale)
      }
    }

    frame = requestAnimationFrame(update)
    return () => {
      cancelAnimationFrame(frame)
      clearTimeout(closeTimer)
    }
  }, [payout, amount, scale])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1, x: shake ? [0, -shake, shake, -shake, 0] : 0 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-100 flex cursor-pointer flex-col items-center justify-center overflow-hidden bg-zeus-black/95 px-4 backdrop-blur-[15px]"
    >
      <motion.div
        animate={{ scale: [1, 1.4, 1], opacity: [0.2, 0.5, 0.2], backgroundColor: current.color }}
        transition={{ duration: 1.5, repeat: Infinity }}
        className="absolute -z-10 size-200 rounded-full blur-[150px]"
      />

      <AnimatePresence mode="wait">
        <motion.h2
          key={current.label}
          initial={{ scale: 0.2, opacity: 0, rotate: -10 }}
          animate={{ scale: 1, opacity: 1, rotate: 0 }}
          exit={{ scale: 1.5, opacity: 0 }}
          className="zeus-overlay-title"
          style={{ textShadow: `0 0 40px ${current.color}, 0 0 80px ${current.color}` }}
        >
          {labels[current.label]}
        </motion.h2>
      </AnimatePresence>

      <motion.div
        animate={{ scale: [1, 1.02, 1] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        className="zeus-overlay-amount"
        style={{ textShadow: `0 0 60px ${current.color}` }}
      >
        {formatCount(shown)}
        <span className="text-[0.4em] opacity-80">{currency}</span>
      </motion.div>

      <div className="zeus-overlay-label" style={{ border: `2px solid ${current.color}` }}>
        {labels.total_win}
      </div>

      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {coins.map((coin, index) => {
          const isCoin = index % 2 === 0
          return (
            <motion.div
              key={index}
              initial={{ y: -100, rotate: 0 }}
              animate={{ y: '105vh', rotate: coin.rotate, x: coin.drift }}
              transition={{ duration: coin.duration, repeat: Infinity, delay: coin.delay, ease: 'linear' }}
              className="absolute"
              style={{
                left: `${coin.startX}%`,
                width: coin.size,
                height: coin.size,
                zIndex: coin.front ? 90 : -5,
                willChange: 'transform',
                borderRadius: isCoin ? '50%' : 4,
                background: isCoin
                  ? 'radial-gradient(ellipse at top left, var(--color-zeus-gold-light) 0%, var(--color-zeus-yellow) 50%, var(--color-zeus-coin-edge) 100%)'
                  : current.color,
                boxShadow: `0 0 8px ${isCoin ? 'var(--color-zeus-yellow)' : current.color}`,
              }}
            />
          )
        })}
      </div>
    </motion.div>
  )
}
