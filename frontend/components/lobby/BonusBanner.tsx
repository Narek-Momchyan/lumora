'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
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
    <Card tone="hero" large padding="none" className="flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-10">
      <div>
        <p className="text-xs font-semibold tracking-wide text-lime uppercase">{labels.bonus_eyebrow}</p>
        <h2 className="mt-2 font-heading text-3xl font-bold sm:text-4xl">{labels.bonus_title}</h2>
        <p className="mt-2 text-sm text-text sm:text-[15px]">{labels.bonus_text}</p>
      </div>

      <div className="shrink-0 space-y-2 sm:text-right">
        {ready && (
          <Button size="lg" disabled={pending} onClick={claim} className="px-6">
            {pending ? labels.bonus_claiming : labels.bonus_claim_button}
          </Button>
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
    </Card>
  )
}
