'use client'

import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { formatCount, jackpotLabel } from '@/lib/zeus'
import type { ZeusPageLabels } from '@/types/zeus'
import { makeJackpotCoins } from './effects'

const COUNT_MS = 4000
const HOLD_MS = 3500
const COINS = 120

const TIER_COLORS: Record<string, string> = {
  GRAND: 'var(--color-zeus-yellow)',
  MAJOR: 'var(--color-zeus-red)',
  MINOR: 'var(--color-zeus-purple)',
  MINI: 'var(--color-zeus-sky)',
}

function tierIcon(tier: string, labels: ZeusPageLabels) {
  const icons: Record<string, string> = {
    GRAND: labels.jackpot_icon_grand,
    MAJOR: labels.jackpot_icon_major,
    MINOR: labels.jackpot_icon_minor,
    MINI: labels.jackpot_icon_mini,
  }
  return icons[tier]
}

interface JackpotWinOverlayProps {
  tier: string
  amount: string
  currency: string
  labels: ZeusPageLabels
  scale: number
  onClose: () => void
}

export default function JackpotWinOverlay({ tier, amount, currency, labels, scale, onClose }: JackpotWinOverlayProps) {
  const [shown, setShown] = useState(0)
  const [coins] = useState(() => makeJackpotCoins(COINS))
  const close = useRef(onClose)
  const color = TIER_COLORS[tier] ?? TIER_COLORS.MINI

  useEffect(() => {
    close.current = onClose
  })

  useEffect(() => {
    const end = Number(amount)
    const duration = COUNT_MS * scale
    const start = performance.now()
    let frame = 0
    let closeTimer: ReturnType<typeof setTimeout>

    function update(now: number) {
      // The first frame's time can be a moment before `start`.
      const progress = Math.min(Math.max(now - start, 0) / duration, 1)
      setShown((1 - Math.pow(1 - progress, 3)) * end)
      if (progress < 1) frame = requestAnimationFrame(update)
      else closeTimer = setTimeout(() => close.current(), HOLD_MS * scale)
    }

    frame = requestAnimationFrame(update)
    return () => {
      cancelAnimationFrame(frame)
      clearTimeout(closeTimer)
    }
  }, [amount, scale])

  return (
    <motion.div
      role="status"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-200 flex cursor-pointer flex-col items-center justify-center overflow-hidden bg-zeus-black/97 px-4"
    >
      <motion.div
        animate={{ scale: [1, 1.6, 1], opacity: [0.3, 0.7, 0.3], backgroundColor: color }}
        transition={{ duration: 1.2, repeat: Infinity }}
        className="absolute -z-10 size-175 rounded-full blur-[180px]"
      />

      <motion.div
        animate={{ scale: [1, 1.3, 1], rotate: [0, 10, -10, 0] }}
        transition={{ duration: 1.5, repeat: Infinity }}
        className="mb-2 text-[clamp(3.5rem,10vh,5.5rem)] leading-none"
      >
        {tierIcon(tier, labels)}
      </motion.div>

      <motion.h2
        initial={{ scale: 0, rotate: -15 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 15 }}
        className="m-0 text-center font-heading text-[clamp(2rem,8vw,4.5rem)] font-black tracking-widest text-zeus-white uppercase"
        style={{ textShadow: `0 0 40px ${color}, 0 0 80px ${color}` }}
      >
        {labels.jackpot_won.replace('{tier}', jackpotLabel(tier, labels))}
      </motion.h2>

      <motion.div
        animate={{ scale: [1, 1.04, 1] }}
        transition={{ duration: 0.3, repeat: Infinity }}
        className="zeus-overlay-amount mt-2"
        style={{ textShadow: `0 0 60px ${color}` }}
      >
        {formatCount(shown)}
        <span className="text-[0.4em] opacity-70">{currency}</span>
      </motion.div>

      <div className="mt-6 text-sm tracking-widest text-zeus-white/60 uppercase">{labels.tap_to_continue}</div>

      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {coins.map((coin, index) => (
          <motion.div
            key={index}
            initial={{ y: -80 }}
            animate={{ y: '110vh', rotate: coin.rotate }}
            transition={{ duration: coin.duration, repeat: Infinity, delay: coin.delay, ease: 'linear' }}
            className="absolute rounded-full shadow-[0_0_12px_var(--color-zeus-yellow)]"
            style={{
              left: `${coin.x}%`,
              width: coin.width,
              height: coin.height,
              background:
                'radial-gradient(ellipse at top left, var(--color-zeus-gold-light) 0%, var(--color-zeus-yellow) 55%, var(--color-zeus-coin-edge) 100%)',
            }}
          />
        ))}
      </div>
    </motion.div>
  )
}
