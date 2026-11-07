'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import SoundButton from '@/components/SoundButton'
import Badge from '@/components/ui/Badge'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { BALL_DROP_MS, FIRST_CHIP, PAUSE_MS, spotKey } from '@/lib/roulette'
import useGameSounds from '@/lib/useGameSounds'
import { fromCents, toCents } from '@/lib/wallet'
import type { Game } from '@/types/game'
import type { GameSound } from '@/types/sound'
import type { LastRound, RoulettePageLabels, RouletteSlip, RouletteSlipResult } from '@/types/roulette'
import BettingBoard from './BettingBoard'
import LiveTable from './LiveTable'
import ResultHistory from './ResultHistory'
import RoundFooter from './RoundFooter'
import RoundPanel from './RoundPanel'
import useBetSlip from './useBetSlip'
import useRouletteFeed from './useRouletteFeed'
import useSecondsLeft from './useSecondsLeft'
import Wheel from './Wheel'
import YourBets from './YourBets'

interface RouletteGameProps {
  game: Game
  slips: RouletteSlip[]
  mySeat: string
  currency: string
  labels: RoulettePageLabels
  sounds: GameSound[]
}

export default function RouletteGame({ game, slips, mySeat, currency, labels, sounds }: RouletteGameProps) {
  const router = useRouter()
  const { round, history, bets, payouts, connected, clockOffset } = useRouletteFeed()
  const slip = useBetSlip(round?.number)

  const [mySlips, setMySlips] = useState(slips)
  const [chip, setChip] = useState(FIRST_CHIP)
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState({ round: 0, text: '' })
  const [paidRound, setPaidRound] = useState(0) // the round whose payouts have been read back

  const isOpen = connected && round?.status === 'betting'
  const error = failure.round === round?.number ? failure.text : ''
  const placed = mySlips.filter((row) => row.round === round?.number).flatMap((row) => row.lines)

  let deadline: number | null = null
  if (round?.status === 'betting') deadline = Date.parse(round.betting_ends_at)
  if (round?.status === 'spinning' && round.spin_ends_at) deadline = Date.parse(round.spin_ends_at)
  if (round?.status === 'settled' && round.settled_at) deadline = Date.parse(round.settled_at) + PAUSE_MS
  const seconds = useSecondsLeft(deadline, clockOffset)

  const amounts: Record<string, number> = {}
  for (const line of placed) amounts[spotKey(line)] = (amounts[spotKey(line)] ?? 0) + toCents(line.amount)
  for (const line of slip.lines) amounts[spotKey(line)] = (amounts[spotKey(line)] ?? 0) + line.cents

  const settledNumber = round?.status === 'settled' ? round.number : null
  const playedThisRound = placed.length > 0

  // The server knows what each line paid: read it back, with the new balance in the header.
  useEffect(() => {
    if (settledNumber === null || !playedThisRound) return
    apiFetch<RouletteSlip[]>('/roulette_bets')
      .then((rows) => {
        setMySlips(rows)
        setPaidRound(settledNumber)
      })
      .catch(() => {})
    router.refresh()
  }, [settledNumber, playedThisRound, router])

  const payoutCents = placed.reduce((sum, line) => sum + toCents(line.payout), 0)
  const stakeCents = placed.reduce((sum, line) => sum + toCents(line.amount), 0)

  // Sounds: only files uploaded in the admin play, and the player starts with the sound off.
  const { muted, volume, play, toggleMuted, setVolume } = useGameSounds(sounds)
  const heard = useRef({ rounds: new Set<number>(), announced: 0 }) // rounds seen before they settled; the last result announced
  const before = useRef<{ number: number; status: string } | null>(null)

  // Betting opens and the wheel starts. The first state the page sees (a snapshot) announces nothing, so
  // opening the page in the middle of a round is quiet.
  useEffect(() => {
    if (!round) return
    const previous = before.current
    before.current = { number: round.number, status: round.status }
    if (round.status !== 'settled') heard.current.rounds.add(round.number)
    if (!previous || (previous.number === round.number && previous.status === round.status)) return
    if (round.status === 'betting') play('round_start')
    if (round.status === 'spinning') play('roulette_spin')
  }, [round, play])

  // The ball drops in the last 1.6 s of the spin, by the server's clock. Joining so late that it is almost over
  // plays nothing.
  useEffect(() => {
    if (round?.status !== 'spinning' || !round.spin_ends_at) return
    const delay = Date.parse(round.spin_ends_at) - BALL_DROP_MS - (Date.now() + (clockOffset.current ?? 0))
    if (delay < 300 - BALL_DROP_MS) return
    const timer = window.setTimeout(() => play('roulette_ball_drop'), Math.max(0, delay))
    return () => window.clearTimeout(timer)
  }, [round?.status, round?.spin_ends_at, clockOffset, play])

  // After the settlement, once what each line paid has been read back: win or lose, only if I had a bet and
  // was here for the round (a result that is already on the page when it opens is not announced).
  useEffect(() => {
    if (settledNumber === null || paidRound !== settledNumber || heard.current.announced === settledNumber) return
    heard.current.announced = settledNumber
    if (!heard.current.rounds.has(settledNumber) || !playedThisRound) return
    play(payoutCents > 0 ? 'win' : 'lose')
  }, [settledNumber, paidRound, playedThisRound, payoutCents, play])
  const won =
    round?.status === 'settled' && payoutCents > 0
      ? {
          payout: fromCents(payoutCents),
          net: `${payoutCents >= stakeCents ? '+' : '−'}${fromCents(Math.abs(payoutCents - stakeCents))}`,
          wonLines: placed.filter((line) => toCents(line.payout) > 0).length,
          totalLines: placed.length,
        }
      : null

  function fail(exception: unknown) {
    if (!(exception instanceof ApiError)) throw exception
    setFailure({ round: round?.number ?? 0, text: errorDetail(exception, labels.server_unreachable) })
  }

  async function placeBets() {
    setPending(true)
    setFailure({ round: 0, text: '' })

    try {
      const result = await apiFetch<RouletteSlipResult>('/roulette_bets', {
        method: 'POST',
        body: {
          key: crypto.randomUUID(),
          lines: slip.lines.map(({ bet_type, value, cents }) => ({ bet_type, value, amount: fromCents(cents) })),
        },
      })
      setMySlips((rows) => [result, ...rows])
      slip.clear()
      play('bet_placed')
      router.refresh() // the balance in the header comes from the server
    } catch (exception) {
      fail(exception)
    }

    setPending(false)
  }

  async function rebet() {
    setPending(true)
    setFailure({ round: 0, text: '' })

    try {
      const { lines } = await apiFetch<LastRound>('/roulette_bets/last_round')
      if (lines.length) {
        slip.replace(lines.map(({ bet_type, value, amount }) => ({ bet_type, value, cents: toCents(amount) })))
      }
    } catch (exception) {
      fail(exception)
    }

    setPending(false)
  }

  const shown = round?.status === 'settled' ? history.slice(1) : history
  const last = shown[0] ?? null

  const players = new Set(bets.map((bet) => bet.seat)).size

  return (
    // On a laptop everything stays on one screen. A phone's upright board is too tall for that.
    <div className="grid gap-4 md:h-[calc(100dvh-12rem)] md:min-h-[34rem] md:grid-cols-[minmax(0,1fr)_18rem] lg:h-[calc(100dvh-9.5rem)] lg:grid-cols-[minmax(0,1fr)_22.5rem] lg:gap-6">
      <div className="relative flex min-h-0 min-w-0 flex-col gap-4">
        <ResultHistory results={history} />

        <section className="relative flex h-72 min-h-0 items-center gap-4 overflow-hidden rounded-3xl border border-border bg-linear-to-b from-accent2/10 to-bg px-3 pt-11 pb-3 sm:p-5 sm:pt-5 md:h-auto md:flex-[1.6] xl:gap-8 xl:px-8">
          <div className="flex h-full min-h-0 min-w-0 flex-1 items-center justify-center">
            <Wheel round={round} previous={last?.result} clockOffset={clockOffset} />
          </div>
          <div className="w-36 shrink-0 sm:w-48 xl:w-64">
            <RoundPanel round={round} connected={connected} seconds={seconds} last={last} won={won} labels={labels} />
          </div>
          <Badge tone="accent2" dot className="absolute top-3 right-3 sm:top-5 sm:right-5">
            <span className="tracking-wide uppercase">{labels.live}</span>
            <span className="font-normal text-muted">{labels.players_count.replace('{count}', String(players))}</span>
          </Badge>
        </section>

        <div className="min-h-0 md:flex-1">
          <BettingBoard
            round={round}
            isOpen={isOpen}
            amounts={amounts}
            labels={labels}
            onBet={(spot) => slip.add(spot, chip * 100)}
          />
        </div>

        <RoundFooter round={round} rtp={game.rtp} labels={labels} />
      </div>

      <div className="flex min-h-0 min-w-0 flex-col gap-4">
        <SoundButton muted={muted} volume={volume} onToggle={toggleMuted} onVolume={setVolume} labels={labels} />
        <YourBets
          round={round}
          isOpen={isOpen}
          seconds={seconds}
          chip={chip}
          draft={slip.lines}
          placed={placed}
          paid={paidRound === round?.number}
          pending={pending}
          error={error}
          currency={currency}
          labels={labels}
          onChip={setChip}
          onUndo={slip.undo}
          onClear={slip.clear}
          onDouble={slip.double}
          onRebet={rebet}
          onPlace={placeBets}
        />
        <LiveTable bets={bets} payouts={payouts} round={round} mySeat={mySeat} currency={currency} labels={labels} />
      </div>
    </div>
  )
}
