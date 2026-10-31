'use client'

import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { formatBalance } from '@/lib/wallet'
import { BET_STEPS, SPEEDS, bonusCost, payToLc } from '@/lib/zeus'
import type { Game } from '@/types/game'
import type { HeaderLabels } from '@/types/header'
import type {
  JackpotPool,
  SlotSound,
  SlotSpinRecord,
  SpeedMode,
  SymbolDetails,
  ZeusPageLabels,
} from '@/types/zeus'
import BuyBonusDialog from './BuyBonusDialog'
import ControlBar from './ControlBar'
import GameHero from './GameHero'
import JackpotPanel from './JackpotPanel'
import MultiplierPanel from './MultiplierPanel'
import RoundOverlay from './RoundOverlay'
import SlotGrid from './SlotGrid'
import SpinHistory from './SpinHistory'
import useSlotSounds from './useSlotSounds'
import useZeusRound from './useZeusRound'

interface ZeusGameProps {
  game: Game
  symbols: SymbolDetails
  sounds: SlotSound[]
  pools: JackpotPool[]
  spins: SlotSpinRecord[]
  balance: string
  header: HeaderLabels
  labels: ZeusPageLabels
}

export default function ZeusGame({ game, symbols, sounds, pools, spins, balance, header, labels }: ZeusGameProps) {
  const betSteps = BET_STEPS.filter((step) => {
    const bet = Number(step)
    return bet >= Number(game.min_bet) && bet <= Number(game.max_bet)
  })

  const [betIndex, setBetIndex] = useState(betSteps.indexOf('1.00'))
  const [speed, setSpeed] = useState<SpeedMode>('normal')
  const [autoLeft, setAutoLeft] = useState(0)
  const [askBuy, setAskBuy] = useState(false)
  const [poolAmounts, setPoolAmounts] = useState(
    Object.fromEntries(pools.map(({ tier, amount }) => [tier, amount])),
  )
  const [wallet, setWallet] = useState(balance)

  const audio = useSlotSounds(sounds)
  const round = useZeusRound({
    sounds: audio,
    speed,
    fallbackError: labels.server_unreachable,
    onPools: setPoolAmounts,
    onBalance: setWallet,
  })

  const amount = betSteps[betIndex]
  const price = bonusCost(amount)
  const priceText = formatBalance(price.toFixed(2))
  const isBusy = round.isPlaying || round.overlay !== null
  const pressSpin = useRef(() => {})

  function playOrSkip() {
    if (round.isPlaying) round.skip()
    else if (autoLeft === 0) round.spin(amount)
  }

  useEffect(() => {
    pressSpin.current = playOrSkip
  })

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.code !== 'Space' || event.repeat) return
      if ((event.target as HTMLElement).closest('input, button, a, textarea')) return
      event.preventDefault()
      pressSpin.current()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    if (autoLeft === 0 || isBusy) return

    const timer = setTimeout(async () => {
      if (Number(wallet) < Number(amount)) {
        setAutoLeft(0)
        return
      }
      setAutoLeft((left) => left - 1)
      const played = await round.spin(amount)
      if (!played) setAutoLeft(0)
    }, SPEEDS[speed].next)

    return () => clearTimeout(timer)
  })

  const lastWin = round.lastPayout && Number(round.lastPayout) > 0 ? round.lastPayout : null
  const liveWin = round.roundPay > 0 ? payToLc(round.roundPay, amount) : null

  return (
    <div className="space-y-4">
      <motion.div
        animate={round.shake ? { x: [0, -3, 3, 0] } : { x: 0 }}
        transition={{ duration: 0.25 }}
        className="flex items-center justify-between gap-3"
      >
        <div className="min-w-0">
          <h1 className="truncate font-heading text-lg font-bold sm:text-2xl">
            {round.inBonus ? labels.free_spins_title : labels.game_title}
          </h1>
          <p className="truncate text-xs text-muted">
            {round.inBonus
              ? labels.free_spins_left.replace('{count}', String(round.freeSpinsLeft))
              : labels.tagline}
          </p>
        </div>

        <button
          type="button"
          aria-pressed={audio.muted}
          onClick={audio.toggleMuted}
          className="shrink-0 rounded-xl border border-border bg-surface px-3 py-2 text-xs text-muted hover:text-text"
        >
          {audio.muted ? labels.unmute : labels.mute}
        </button>
      </motion.div>

      <JackpotPanel pools={poolAmounts} currency={header.currency} labels={labels} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,12rem)_minmax(0,1fr)_minmax(0,10rem)] lg:items-start">
        <GameHero image={game.image} attacking={round.lightning} />

        <div className="relative min-w-0">
          <AnimatePresence>
            {round.tumble > 0 && round.isPlaying && (
              <motion.p
                key={round.tumble}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 rounded-full border border-cyan bg-surface px-3 py-1 text-xs font-semibold whitespace-nowrap text-cyan"
              >
                {labels.tumble.replace('{count}', String(round.tumble))}
              </motion.p>
            )}
          </AnimatePresence>

          <SlotGrid
            grid={round.grid}
            spinNumber={round.spinNumber}
            winningCells={round.winningCells}
            symbols={symbols}
            speed={speed}
            inBonus={round.inBonus}
          />
        </div>

        <MultiplierPanel collected={round.collected} total={round.multiplier} labels={labels} />
      </div>

      {round.error && (
        <p role="alert" className="text-sm text-danger">
          {round.error}
        </p>
      )}

      <ControlBar
        amount={amount}
        canLower={betIndex > 0}
        canRaise={betIndex < betSteps.length - 1}
        winText={round.isPlaying ? liveWin : lastWin}
        isPlaying={round.isPlaying}
        inBonus={round.inBonus}
        multiplier={round.multiplier}
        speed={speed}
        autoLeft={autoLeft}
        canBuyBonus={Number(wallet) >= price}
        bonusPrice={priceText}
        currency={header.currency}
        labels={labels}
        onLower={() => setBetIndex(betIndex - 1)}
        onRaise={() => setBetIndex(betIndex + 1)}
        onSpeed={setSpeed}
        onSpin={() => round.spin(amount)}
        onSkip={round.skip}
        onBuyBonus={() => setAskBuy(true)}
        onAutoStart={setAutoLeft}
        onAutoStop={() => setAutoLeft(0)}
      />

      <SpinHistory spins={spins} currency={header.currency} labels={labels} />

      {askBuy && (
        <BuyBonusDialog
          price={`${priceText} ${header.currency}`}
          labels={labels}
          onCancel={() => setAskBuy(false)}
          onConfirm={() => {
            setAskBuy(false)
            round.spin(amount, true)
          }}
        />
      )}

      <AnimatePresence>
        {round.overlay && (
          <RoundOverlay
            key={round.overlay.kind}
            overlay={round.overlay}
            currency={header.currency}
            labels={labels}
            onClose={round.closeOverlay}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
