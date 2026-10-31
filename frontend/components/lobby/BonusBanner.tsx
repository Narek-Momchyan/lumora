'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { formatDateTime } from '@/lib/wallet'
import type { LobbyPageLabels } from '@/types/game'
import type { Wallet } from '@/types/wallet'

interface BonusBannerProps {
  wallet: Wallet | null
  ready: boolean
  labels: LobbyPageLabels
}

export default function BonusBanner({ wallet, ready, labels }: BonusBannerProps) {
  const router = useRouter()
  const [pending, setPending] = useState(false)
  const [claimed, setClaimed] = useState(false)
  const [error, setError] = useState('')

  async function claim() {
    setPending(true)
    setError('')

    try {
      await apiFetch('/bonus', { method: 'POST' })
      setClaimed(true)
    } catch (exception) {
      if (!(exception instanceof ApiError)) throw exception
      setError(errorDetail(exception, labels.server_unreachable))
    }

    setPending(false)
    router.refresh() // the balance in the header and the next bonus time come from the server
  }

  const nextBonus = wallet?.bonus_available_at

  return (
    <section className="flex flex-col gap-6 rounded-3xl bg-linear-to-r from-magenta/30 via-surface2 to-cyan/60 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-10">
      <div>
        <p className="text-xs font-semibold text-lime">{labels.bonus_eyebrow}</p>
        <h1 className="mt-2 font-heading text-3xl font-bold sm:text-4xl">{labels.bonus_title}</h1>
        <p className="mt-2 text-sm text-text">{labels.bonus_text}</p>
      </div>

      <div className="shrink-0 space-y-2 sm:text-right">
        {ready && (
          <button
            type="button"
            disabled={pending}
            onClick={claim}
            className="rounded-xl bg-linear-to-r from-cyan to-magenta px-6 py-3 text-sm font-semibold text-bg shadow-lg shadow-cyan/20 transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {pending ? labels.bonus_claiming : labels.bonus_claim_button}
          </button>
        )}

        {claimed && <p className="text-sm font-semibold text-lime">{labels.bonus_claimed}</p>}

        {!ready && nextBonus && (
          // The server and the browser can be in different time zones.
          <p suppressHydrationWarning className="text-sm text-text">
            {labels.bonus_next.replace('{time}', formatDateTime(nextBonus))}
          </p>
        )}

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
      </div>
    </section>
  )
}
