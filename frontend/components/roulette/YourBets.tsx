import { CHIPS, multiplierOf, spotKey, spotLabel } from '@/lib/roulette'
import { formatBalance, fromCents, toCents } from '@/lib/wallet'
import type { DraftLine, RoulettePageLabels, RouletteRound, SlipLine } from '@/types/roulette'
import Chip from './Chip'

const STEP_BUTTON =
  'rounded-lg border border-border bg-surface2 py-1.5 text-xs font-medium transition-colors hover:enabled:border-cyan disabled:opacity-40'
const MAIN_BUTTON =
  'w-full truncate rounded-lg bg-linear-to-r from-cyan to-magenta px-3 py-2.5 text-sm font-semibold text-bg transition-opacity hover:enabled:opacity-90 disabled:from-surface2 disabled:to-surface2 disabled:text-muted'

interface YourBetsProps {
  round: RouletteRound | null
  isOpen: boolean
  seconds: number
  chip: number
  draft: DraftLine[]
  placed: SlipLine[]
  paid: boolean // the lines already have their payouts, so a win can't show as a loss for a moment
  pending: boolean
  error: string
  currency: string
  labels: RoulettePageLabels
  onChip: (chip: number) => void
  onUndo: () => void
  onClear: () => void
  onDouble: () => void
  onRebet: () => void
  onPlace: () => void
}

export default function YourBets({
  round,
  isOpen,
  seconds,
  chip,
  draft,
  placed,
  paid,
  pending,
  error,
  currency,
  labels,
  onChip,
  onUndo,
  onClear,
  onDouble,
  onRebet,
  onPlace,
}: YourBetsProps) {
  const settled = round?.status === 'settled'
  const draftCents = draft.reduce((sum, line) => sum + line.cents, 0)
  const placedCents = placed.reduce((sum, line) => sum + toCents(line.amount), 0)
  const winCents = placed.reduce((sum, line) => sum + toCents(line.payout), 0)
  const count = placed.length + draft.length

  function statusText() {
    if (round?.status === 'spinning') return labels.bets_closed
    const number = labels.round_number.replace('{number}', String(round?.number ?? ''))
    if (settled || !count) return number
    return `${labels.bets_count.replace('{count}', String(count))} · ${number}`
  }

  function buttonText() {
    if (isOpen) return `${labels.place_bets} · ${formatBalance(fromCents(draftCents))} ${currency}`
    if (settled) return labels.next_round_in.replace('{seconds}', String(seconds))
    const waiting = labels.result_in.replace('{seconds}', String(seconds))
    return `${labels.bets_closed} · ${waiting}`
  }

  return (
    <section className="flex min-h-0 flex-col gap-2 rounded-2xl border border-border bg-surface p-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="truncate font-heading text-sm font-semibold">{labels.your_bets}</h2>
        <p className="shrink-0 text-xs text-muted">{statusText()}</p>
      </div>

      <div>
        <p className="mb-1 text-xs text-muted">{labels.chip_value}</p>
        <div className="flex justify-between gap-1">
          {CHIPS.map((value) => (
            <button
              key={value}
              type="button"
              disabled={!isOpen}
              onClick={() => onChip(value)}
              aria-label={String(value)}
              aria-pressed={chip === value}
              className={`rounded-full transition-opacity disabled:opacity-40 ${
                chip === value ? 'ring-2 ring-cyan ring-offset-2 ring-offset-surface' : ''
              }`}
            >
              <Chip value={value} className="size-8 text-[10px]" />
            </button>
          ))}
        </div>
      </div>

      {count > 0 && (
        <ul className="max-h-24 min-h-0 space-y-1 overflow-y-auto rounded-lg bg-surface2 p-2 text-xs [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {placed.map((line) => {
            const won = toCents(line.payout) > 0
            return (
              <li key={`placed-${spotKey(line)}-${line.amount}`} className="grid grid-cols-[minmax(0,1fr)_auto_4.5rem] gap-2">
                <span className="truncate">{spotLabel(line, labels)}</span>
                <span className="text-muted">{line.multiplier - 1}:1</span>
                <span className={`text-right font-semibold tabular-nums ${paid ? (won ? 'text-lime' : 'text-danger') : ''}`}>
                  {paid && (won ? `+${formatBalance(line.payout)}` : `−${formatBalance(line.amount)}`)}
                  {!paid && formatBalance(line.amount)} {currency}
                </span>
              </li>
            )
          })}
          {draft.map((line) => (
            <li key={`draft-${spotKey(line)}`} className="grid grid-cols-[minmax(0,1fr)_auto_4.5rem] gap-2 text-muted">
              <span className="truncate">{spotLabel(line, labels)}</span>
              <span>{multiplierOf(line.bet_type) - 1}:1</span>
              <span className="text-right font-semibold tabular-nums">
                {formatBalance(fromCents(line.cents))} {currency}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="grid grid-cols-4 gap-1.5">
        <button type="button" disabled={!isOpen || !draft.length} onClick={onUndo} className={STEP_BUTTON}>
          {labels.undo}
        </button>
        <button type="button" disabled={!isOpen || !draft.length} onClick={onClear} className={STEP_BUTTON}>
          {labels.clear}
        </button>
        <button type="button" disabled={!isOpen || !draft.length} onClick={onDouble} className={STEP_BUTTON}>
          {labels.double}
        </button>
        <button type="button" disabled={!isOpen || pending} onClick={onRebet} className={STEP_BUTTON}>
          {labels.rebet}
        </button>
      </div>

      <div className="flex items-baseline justify-between gap-3 text-xs">
        <span className="text-muted">{settled ? labels.total_win : labels.total_bet}</span>
        <span className={`text-sm font-semibold tabular-nums ${paid && winCents ? 'text-lime' : ''}`}>
          {paid
            ? `${winCents ? '+' : ''}${formatBalance(fromCents(winCents))}`
            : formatBalance(fromCents(settled ? 0 : placedCents + draftCents))}{' '}
          {currency}
        </span>
      </div>

      <button type="button" disabled={!isOpen || pending || !draft.length} onClick={onPlace} className={MAIN_BUTTON}>
        {buttonText()}
      </button>

      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </section>
  )
}
