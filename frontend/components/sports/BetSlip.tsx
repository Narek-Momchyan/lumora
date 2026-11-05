'use client'

import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import SectionTitle from '@/components/ui/SectionTitle'
import Tabs from '@/components/ui/Tabs'
import { slip } from '@/lib/slip-store'
import type { SlipMode, SlipPick } from '@/lib/slip-store'
import {
  MAX_STAKE_CENTS,
  STAKE_STEPS,
  centsToString,
  dayWord,
  marketName,
  pickName,
  potentialWinCents,
  stakeToCents,
  timeOf,
  toCentsExact,
  totalOddsCents,
  trend,
} from '@/lib/sports'
import useNow from '@/lib/useNow'
import { formatBalance, toCents } from '@/lib/wallet'
import { useOddsMap, useSlip, useSlipContext } from './SlipProvider'

const MODES: SlipMode[] = ['single', 'express']

// The bet slip (designs 06, 07): the same picks on every page, single or express.
export default function BetSlip() {
  const context = useSlipContext()
  const state = useSlip()
  const oddsMap = useOddsMap()
  const now = useNow(5000)
  const reduce = useReducedMotion()
  if (!context) return null

  const { ui, bet, balance, currency, status, error, note } = context
  const count = state.picks.length

  const views = state.picks.map((pick) => {
    const live = oddsMap.get(pick.selection)
    const current = live?.odds ?? pick.odds
    return {
      pick,
      current,
      previous: live?.previous ?? null,
      changed: current !== pick.odds,
      closed: live?.open === false || Date.parse(pick.kickoff) <= now,
    }
  })
  const changed = views.some((view) => view.changed)
  const closed = views.some((view) => view.closed)
  const stakeCents = stakeToCents(state.stake)
  const stakeValid = Number.isFinite(stakeCents) && stakeCents > 0
  const stake = BigInt(stakeValid ? stakeCents : 0)

  // express: one bet at the product of the odds; single: a bet per pick, each with this stake
  const express = state.mode === 'express'
  const total = totalOddsCents(views.map((view) => view.current))
  const winCents = express
    ? potentialWinCents(stake, total)
    : views.reduce((sum, view) => sum + potentialWinCents(stake, toCentsExact(view.current)), BigInt(0))
  const stakeTotal = express ? stake : stake * BigInt(count)
  const tooFew = express && count < 2

  function setStake(value: string) {
    slip.setStake(value.replace(',', '.').replace(/[^\d.]/g, ''))
  }

  function addToStake(amount: number) {
    const cents = Number.isFinite(stakeCents) ? stakeCents : 0
    slip.setStake(centsToString(BigInt(cents + amount * 100)))
  }

  function maxStake() {
    const most = balance ? Math.min(toCents(balance), MAX_STAKE_CENTS) : MAX_STAKE_CENTS
    slip.setStake(centsToString(BigInt(most)))
  }

  function acceptOdds() {
    slip.acceptOdds(Object.fromEntries(views.map((view) => [view.pick.selection, view.current])))
  }

  function describe(pick: SlipPick) {
    const teams = { home: { short_name: pick.home, name: pick.home }, away: { short_name: pick.away, name: pick.away } }
    const when = `${dayWord(pick.kickoff, ui, new Date(now))} ${timeOf(pick.kickoff)}`
    return {
      title: pickName(pick.kind, pick.line, pick.code, teams, bet),
      subtitle: `${marketName(pick.kind, bet)} · ${pick.home} – ${pick.away} · ${when}`,
    }
  }

  let action = (
    <Button
      size="lg"
      block
      disabled={count === 0 || !stakeValid || closed || tooFew || status === 'placing'}
      suffix={`· ${formatBalance(centsToString(stakeTotal))} ${currency}`}
      onClick={context.place}
    >
      {ui.place_bet}
    </Button>
  )
  if (status === 'placed') {
    action = (
      <Button size="lg" block disabled>
        <motion.span
          initial={reduce ? false : { scale: 0.3 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 14 }}
          className="inline-block"
        >
          ✓
        </motion.span>{' '}
        {ui.bet_placed}
      </Button>
    )
  } else if (changed) {
    action = (
      <Button size="lg" block onClick={acceptOdds}>
        {ui.accept_odds}
      </Button>
    )
  }

  return (
    <Card padding="md" className="scroll-mt-20 space-y-4" id="bet-slip">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <SectionTitle title={ui.slip_title} />
          {count > 0 && (
            <motion.span
              key={count}
              data-slip-badge=""
              initial={reduce ? false : { scale: 1.5 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 14 }}
              className="flex size-5 shrink-0 items-center justify-center rounded-full bg-lime text-xs font-bold text-bg"
            >
              {count}
            </motion.span>
          )}
        </div>
        {count > 0 && (
          <button type="button" onClick={slip.clear} className="shrink-0 text-xs text-muted hover:text-text">
            {ui.clear_all}
          </button>
        )}
      </div>

      <Tabs
        tabs={MODES.map((mode) => ({ id: mode, label: mode === 'single' ? bet.single : bet.express }))}
        value={state.mode}
        onChange={slip.setMode}
      />

      {count === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-surface2/40 px-4 py-6 text-center">
          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
            className="mx-auto size-8 text-accent"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 7h16v3.2a1.8 1.8 0 0 0 0 3.6V17H4v-3.2a1.8 1.8 0 0 0 0-3.6Z" />
            <path d="M10 9v6" strokeDasharray="1.5 2" />
          </svg>
          <p className="mt-3 text-sm font-semibold">{ui.slip_empty_title}</p>
          <p className="mt-1 text-xs text-muted">{ui.slip_empty_text}</p>
        </div>
      ) : (
        <>
          <ul className="space-y-2">
            <AnimatePresence initial={false}>
              {views.map(({ pick, current, previous, changed: moved, closed: isClosed }) => {
                const { title, subtitle } = describe(pick)
                const direction = trend(current, previous)
                return (
                  <motion.li
                    key={pick.selection}
                    layout={!reduce}
                    initial={reduce ? false : { opacity: 0, x: 16 }}
                    animate={{ opacity: isClosed ? 0.5 : 1, x: 0 }}
                    exit={reduce ? undefined : { opacity: 0, x: 16 }}
                    className="flex items-start gap-2 rounded-xl border-l-2 border-accent bg-surface2/60 py-2.5 pr-2 pl-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="flex items-center gap-2 text-sm font-semibold">
                        <span className="truncate">{title}</span>
                        {isClosed && <Badge small>{ui.closed_badge}</Badge>}
                      </p>
                      <p className="truncate text-xs text-muted">{subtitle}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      {moved && <p className="text-[10px] text-muted line-through tabular-nums">{pick.odds}</p>}
                      <p
                        className={`font-heading text-sm font-bold tabular-nums ${
                          moved ? (Number(current) > Number(pick.odds) ? 'text-lime' : 'text-danger') : 'text-accent'
                        }`}
                      >
                        {current}
                        {direction && moved ? (direction === 'up' ? ' ▲' : ' ▼') : ''}
                      </p>
                    </div>
                    <button
                      type="button"
                      aria-label={ui.clear_all}
                      onClick={() => slip.remove(pick.selection)}
                      className="shrink-0 px-1 text-xs text-muted hover:text-text"
                    >
                      ✕
                    </button>
                  </motion.li>
                )
              })}
            </AnimatePresence>
          </ul>

          {express && (
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted">{ui.total_odds}</span>
              <span className="font-heading font-bold tabular-nums">{centsToString(total)}</span>
            </div>
          )}

          <label className="flex h-12 items-center gap-3 rounded-xl border border-border bg-surface2 px-4 focus-within:border-accent">
            <input
              inputMode="decimal"
              autoComplete="off"
              value={state.stake}
              onChange={(event) => setStake(event.target.value)}
              aria-label={ui.stake_label}
              className="min-w-0 flex-1 bg-transparent text-base font-semibold text-text tabular-nums outline-none"
            />
            <span className="shrink-0 text-xs text-muted">{ui.stake_label}</span>
          </label>

          <div className="grid grid-cols-4 gap-2">
            {STAKE_STEPS.map((step) => (
              <Button key={step} variant="ghost" size="sm" onClick={() => addToStake(step)}>
                +{step}
              </Button>
            ))}
            <Button variant="ghost" size="sm" onClick={maxStake}>
              {ui.max_button}
            </Button>
          </div>

          <div className="flex items-baseline justify-between gap-3">
            <span className="text-sm text-muted">{ui.potential_win}</span>
            <span className="truncate font-heading text-2xl font-bold text-lime tabular-nums">
              {formatBalance(centsToString(winCents))} {currency}
            </span>
          </div>

          {changed && <p className="text-xs text-lime">{note || ui.odds_changed_note}</p>}
          {tooFew && <p className="text-xs text-muted">{ui.min_picks}</p>}
          {error && (
            <p role="alert" className="text-xs text-danger">
              {error}
            </p>
          )}

          {action}
        </>
      )}
    </Card>
  )
}
