'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import SoundButton from '@/components/SoundButton'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import useGameSounds from '@/lib/useGameSounds'
import type { CrashBet, CrashBetResult, CrashPageLabels } from '@/types/crash'
import type { Game } from '@/types/game'
import type { GameSound } from '@/types/sound'
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
  sounds: GameSound[]
}

export default function CrashGame({ game, balance, lastBet, currency, labels, sounds }: CrashGameProps) {
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

  // Sounds: only files uploaded in the admin play, and the player starts with the sound off.
  const { muted, volume, play, stop, toggleMuted, setVolume } = useGameSounds(sounds)
  const openBet = useRef(false) // a bet that has not cashed out: read when the crash comes
  useEffect(() => {
    openBet.current = bet !== null && cashedAt === null
  })

  // The round's sounds. The first state the page sees (a snapshot) announces nothing, so opening the page in
  // the middle of a round is quiet; the flight sound is the exception, it just follows the round.
  const seen = useRef<{ number: number; status: string } | null>(null)
  useEffect(() => {
    if (!round) return
    const before = seen.current
    seen.current = { number: round.number, status: round.status }
    const changed = !before || before.number !== round.number || before.status !== round.status
    if (round.status !== 'flying') stop('crash_flight')
    else if (changed) play('crash_flight', true) // a reconnect mid-flight does not restart the sound
    if (!before || !changed) return
    if (round.status === 'betting') play('round_start')
    if (round.status === 'crashed') {
      play('crash_boom')
      if (openBet.current) play('lose')
    }
  }, [round, play, stop])
  useEffect(() => () => stop('crash_flight'), [stop])

  // My cash-out, by hand or automatic: both show up as `cashedAt`. One that is already there when the page
  // opens is not announced.
  const announced = useRef(cashedAt)
  useEffect(() => {
    if (cashedAt && announced.current !== cashedAt) play('cash_out')
    announced.current = cashedAt
  }, [cashedAt, play])

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
      if (path === '/crash_bets') play('bet_placed')
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
    // Everything stays on one screen: the top bar, the footer and the page's padding take the rest.
    // A very short phone scrolls a little instead of squeezing the chart.
    <div className="grid min-h-[calc(100dvh-12rem)] grid-rows-[minmax(14rem,1fr)_auto] gap-4 md:h-[calc(100dvh-12rem)] md:min-h-96 md:grid-cols-[minmax(0,1fr)_18rem] md:grid-rows-1 lg:h-[calc(100dvh-9.5rem)] lg:grid-cols-[minmax(0,1fr)_22.5rem] lg:gap-6">
      <div className="relative flex min-h-0 min-w-0 flex-col gap-4">
        <CrashHistory points={history} title={labels.history_title} />
        <CrashChart round={round} connected={connected} clockOffset={clockOffset} labels={labels} />
        <RoundFooter round={round} rtp={game.rtp} labels={labels} />
      </div>

      <div className="flex min-h-0 min-w-0 flex-col gap-4">
        <SoundButton muted={muted} volume={volume} onToggle={toggleMuted} onVolume={setVolume} labels={labels} />
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
  )
}
