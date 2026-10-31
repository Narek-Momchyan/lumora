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
import BigWinOverlay from './BigWinOverlay'
import BonusSummary from './BonusSummary'
import BonusTrigger from './BonusTrigger'
import BuyBonusDialog from './BuyBonusDialog'
import ControlBar from './ControlBar'
import GameHero from './GameHero'
import JackpotPanel from './JackpotPanel'
import JackpotWinOverlay from './JackpotWinOverlay'
import LightningBolt from './LightningBolt'
import MultiplierPanel from './MultiplierPanel'
import Particles from './Particles'
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
    autoplay: autoLeft > 0,
    fallbackError: labels.server_unreachable,
    onPools: setPoolAmounts,
    onBalance: setWallet,
  })

  const amount = betSteps[betIndex]
  const price = bonusCost(amount)
  const priceText = formatBalance(price.toFixed(2))
  const { overlay } = round
  const isBusy = round.isPlaying || overlay !== null
  const scale = SPEEDS[speed].overlay
  const pressSpin = useRef(() => {})

  function pressSpinButton() {
    if (round.awaitingSpin) round.startFreeSpin()
    else if (round.isPlaying) round.skip()
    else if (autoLeft === 0) round.spin(amount, { manual: true })
  }

  useEffect(() => {
    pressSpin.current = pressSpinButton
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
    <div className="overflow-x-clip">
      <LightningBolt active={round.lightning} scale={scale} />
      {round.particles > 0 && <Particles key={round.particles} currency={header.currency} scale={scale} />}

      <div
        className={`zeus-table space-y-4 rounded-3xl p-1 sm:p-2 ${round.shake ? 'zeus-shake' : ''} ${
          round.inBonus ? 'zeus-table-bonus' : ''
        }`}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <motion.h1
              animate={round.inBonus ? { scale: [1, 1.02, 1] } : { scale: 1 }}
              transition={round.inBonus ? { duration: 2.5, repeat: Infinity } : undefined}
              className={`truncate font-heading text-lg font-bold sm:text-2xl ${
                round.inBonus ? 'text-zeus-lilac' : 'zeus-gold-text'
              }`}
            >
              {round.inBonus ? labels.free_spins_title : labels.game_title}
            </motion.h1>
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
        </div>

        <JackpotPanel pools={poolAmounts} currency={header.currency} labels={labels} />

        <div className="grid gap-4 lg:grid-cols-[minmax(0,12rem)_minmax(0,1fr)_minmax(0,10rem)] lg:items-start">
          <GameHero image={game.image} attacking={round.lightning} />

          <div className="relative min-w-0">
            <AnimatePresence>
              {round.tumble > 0 && round.isPlaying && (
                <div key={round.tumble} className="absolute -top-3 right-0 left-0 z-30 flex justify-center">
                  <motion.p
                    initial={{ scale: 0.5, opacity: 0, y: 10 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.7, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 22 }}
                    className="rounded-full border border-zeus-gold/60 bg-zeus-gold/20 px-4 py-0.5 text-xs font-bold tracking-widest whitespace-nowrap text-zeus-gold-light uppercase shadow-[0_0_20px_var(--color-zeus-gold)] backdrop-blur-sm"
                  >
                    {labels.tumble.replace('{count}', String(round.tumble))}
                  </motion.p>
                </div>
              )}
            </AnimatePresence>

            <SlotGrid
              grid={round.grid}
              gridId={round.gridId}
              winningCells={round.winningCells}
              symbols={symbols}
              speed={speed}
              inBonus={round.inBonus}
              teaser={round.teaser}
              onLand={() => audio.play('stone_tumble')}
            />
          </div>

          <MultiplierPanel
            collected={round.collected}
            total={round.multiplier}
            inBonus={round.inBonus}
            labels={labels}
          />
        </div>
      </div>

      {round.error && (
        <p role="alert" className="mt-4 text-sm text-danger">
          {round.error}
        </p>
      )}

      <div className="mt-4 space-y-4">
        <ControlBar
          amount={amount}
          canLower={betIndex > 0}
          canRaise={betIndex < betSteps.length - 1}
          winText={round.isPlaying ? liveWin : lastWin}
          isPlaying={round.isPlaying}
          awaitingSpin={round.awaitingSpin}
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
          onSpin={pressSpinButton}
          onBuyBonus={() => setAskBuy(true)}
          onAutoStart={setAutoLeft}
          onAutoStop={() => setAutoLeft(0)}
        />

        <SpinHistory spins={spins} currency={header.currency} labels={labels} />
      </div>

      {askBuy && (
        <BuyBonusDialog
          price={`${priceText} ${header.currency}`}
          labels={labels}
          onCancel={() => setAskBuy(false)}
          onConfirm={() => {
            setAskBuy(false)
            round.spin(amount, { bonusBuy: true })
          }}
        />
      )}

      <AnimatePresence>
        {overlay?.kind === 'big_win' && (
          <BigWinOverlay
            key={overlay.id}
            payout={overlay.payout}
            amount={overlay.amount}
            currency={header.currency}
            labels={labels}
            scale={scale}
            sounds={audio}
            onClose={round.closeOverlay}
          />
        )}
        {overlay?.kind === 'bonus' && (
          <BonusTrigger
            key={overlay.id}
            count={overlay.count}
            labels={labels}
            scale={scale}
            autoClose={autoLeft > 0}
            onClose={round.closeOverlay}
          />
        )}
        {overlay?.kind === 'summary' && (
          <BonusSummary
            key={overlay.id}
            payout={overlay.payout}
            currency={header.currency}
            labels={labels}
            scale={scale}
            autoClose={autoLeft > 0}
            onClose={round.closeOverlay}
          />
        )}
        {overlay?.kind === 'jackpot' && (
          <JackpotWinOverlay
            key={overlay.id}
            tier={overlay.tier}
            amount={overlay.amount}
            currency={header.currency}
            labels={labels}
            scale={scale}
            onClose={round.closeOverlay}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
