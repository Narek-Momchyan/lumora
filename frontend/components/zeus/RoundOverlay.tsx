'use client'

import { motion } from 'motion/react'
import { useEffect } from 'react'
import { formatBalance } from '@/lib/wallet'
import { jackpotLabel } from '@/lib/zeus'
import type { ZeusOverlay, ZeusPageLabels } from '@/types/zeus'

const STAY_ON_SCREEN_MS = { bonus: 1800, big_win: 2500, summary: 4000, jackpot: 5000 }

interface RoundOverlayProps {
  overlay: ZeusOverlay
  currency: string
  labels: ZeusPageLabels
  onClose: () => void
}

function texts(overlay: ZeusOverlay, currency: string, labels: ZeusPageLabels) {
  const money = (value: string) => `${formatBalance(value)} ${currency}`

  switch (overlay.kind) {
    case 'bonus':
      return {
        title: labels.bonus_trigger,
        line: labels.free_spins_won.replace('{count}', String(overlay.count)),
      }
    case 'summary':
      return { title: labels.congratulations, note: labels.total_win, line: money(overlay.payout) }
    case 'big_win':
      return { title: labels[overlay.stage], line: money(overlay.payout) }
    case 'jackpot':
      return {
        title: labels.jackpot_won.replace('{tier}', jackpotLabel(overlay.tier, labels)),
        line: money(overlay.amount),
      }
  }
}

// Closes itself, so autoplay never waits for a click.
export default function RoundOverlay({ overlay, currency, labels, onClose }: RoundOverlayProps) {
  const { title, note, line } = texts(overlay, currency, labels)

  useEffect(() => {
    const timer = setTimeout(onClose, STAY_ON_SCREEN_MS[overlay.kind])
    return () => clearTimeout(timer)
  }, [overlay, onClose])

  return (
    <motion.div
      role="status"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-30 flex items-center justify-center bg-bg/80 p-4"
    >
      <motion.div
        initial={{ scale: 0.7 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 18 }}
        className="w-full max-w-md rounded-3xl border border-cyan bg-surface p-8 text-center"
      >
        <h2 className="font-heading text-3xl font-bold text-lime sm:text-4xl">{title}</h2>
        {note && <p className="mt-4 text-sm text-muted">{note}</p>}
        <p className="mt-2 font-heading text-3xl font-bold text-cyan sm:text-4xl">{line}</p>

        {overlay.kind !== 'bonus' && (
          <button
            type="button"
            onClick={onClose}
            className="mt-6 rounded-xl bg-linear-to-r from-cyan to-magenta px-8 py-3 text-sm font-semibold text-bg"
          >
            {labels.collect}
          </button>
        )}
      </motion.div>
    </motion.div>
  )
}
