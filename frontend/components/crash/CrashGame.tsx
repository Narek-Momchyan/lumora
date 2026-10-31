'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import type { CrashBet, CrashBetResult, CrashPageLabels } from '@/types/crash'
import type { Game } from '@/types/game'
import type { Wallet } from '@/types/wallet'
import BetPanel from './BetPanel'
import CrashChart from './CrashChart'
import CrashHistory from './CrashHistory'
import LiveBets from './LiveBets'
import RoundFooter from './RoundFooter'
import useCrashFeed from './useCrashFeed'

interface CrashGameProps {
  game: Game
  balance: string
  lastBet: CrashBet | null
  currency: string
  labels: CrashPageLabels
}

export default function CrashGame({ game, balance, lastBet, currency, labels }: CrashGameProps) {
  const router = useRouter()
  const { round, history, bets, connected, clockOffset } = useCrashFeed()

  const [wallet, setWallet] = useState(balance)
  const [myBet, setMyBet] = useState(lastBet)
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState({ round: 0, text: '' })

  const bet = myBet && myBet.round === round?.number ? myBet : null
  const live = bets.find(({ id }) => id === `player-${bet?.id}`)
  const cashedAt = live?.multiplier ?? bet?.multiplier ?? null
  const error = failure.round === round?.number ? failure.text : ''

  // The feed also tells about an auto cash-out, which no request of ours started.
  useEffect(() => {
    if (!cashedAt) return
    apiFetch<Wallet>('/wallet')
      .then(({ balance: fresh }) => setWallet(fresh))
      .catch(() => {})
    router.refresh() // the balance in the header comes from the server
  }, [cashedAt, router])

  async function send(path: string, body?: unknown) {
    setPending(true)
    setFailure({ round: 0, text: '' })

    try {
      const result = await apiFetch<CrashBetResult>(path, { method: 'POST', body })
      setMyBet(result)
      setWallet(result.balance)
      router.refresh()
    } catch (exception) {
      if (!(exception instanceof ApiError)) throw exception
      setFailure({ round: round?.number ?? 0, text: errorDetail(exception, labels.server_unreachable) })
    }

    setPending(false)
  }

  function placeBet(amount: string, target: string) {
    send('/crash_bets', { amount, ...(target && { target }) })
  }

  return (
    // Everything stays on one screen: the header, the footer and the page's padding take the rest.
    // A very short phone scrolls a little instead of squeezing the chart.
    <div className="flex min-h-[calc(100dvh-10rem)] flex-col gap-3 md:h-[calc(100dvh-10rem)] md:min-h-80">
      <div className="flex min-w-0 items-center gap-4">
        <h1 className="shrink-0 font-heading text-xl font-bold sm:text-2xl">{labels.game_title}</h1>
        <CrashHistory points={history} title={labels.history_title} />
      </div>

      <div className="grid flex-1 grid-rows-[minmax(11.5rem,1fr)_auto] gap-3 md:min-h-0 md:grid-cols-[minmax(0,1fr)_18rem] md:grid-rows-1 lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-4">
        <div className="relative flex min-h-0 min-w-0 flex-col gap-2">
          <CrashChart round={round} connected={connected} clockOffset={clockOffset} labels={labels} />
          <RoundFooter round={round} rtp={game.rtp} labels={labels} />
        </div>

        <div className="flex min-h-0 min-w-0 flex-col gap-3">
          <BetPanel
            game={game}
            round={round}
            connected={connected}
            clockOffset={clockOffset}
            balance={wallet}
            betAmount={bet?.amount ?? null}
            cashedAt={cashedAt}
            pending={pending}
            error={error}
            currency={currency}
            labels={labels}
            onBet={placeBet}
            onCashOut={() => send('/crash_bets/cash_out')}
          />
          <LiveBets bets={bets} round={round} currency={currency} labels={labels} />
        </div>
      </div>
    </div>
  )
}
