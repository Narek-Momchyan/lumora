import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import SectionTitle from '@/components/ui/SectionTitle'
import { CHIPS, multiplierOf, spotKey, spotLabel } from '@/lib/roulette'
import { formatBalance, fromCents, toCents } from '@/lib/wallet'
import type { DraftLine, RoulettePageLabels, RouletteRound, SlipLine } from '@/types/roulette'
import Chip from './Chip'

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

  // The amount or the seconds go after the cut, so a long translation never hides them.
  function buttonText(): [string, string] {
    if (isOpen) return [labels.place_bets, `· ${formatBalance(fromCents(draftCents))} ${currency}`]
    if (settled) return [labels.next_round_in.replace('{seconds}', String(seconds)), '']
    const waiting = labels.result_in.replace('{seconds}', String(seconds))
    return [labels.bets_closed, `· ${waiting}`]
  }

  const [buttonLabel, buttonSuffix] = buttonText()

  return (
    <Card className="flex min-h-0 shrink-0 flex-col gap-3 lg:gap-4">
      <SectionTitle title={labels.your_bets} aside={statusText()} />

      <div>
        <p className="mb-2 text-xs text-muted lg:text-[13px]">{labels.chip_value}</p>
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
                chip === value ? 'ring-2 ring-accent ring-offset-2 ring-offset-surface' : ''
              }`}
            >
              <Chip value={value} className="size-8 text-[10px] lg:size-10 lg:text-xs" />
            </button>
          ))}
        </div>
      </div>

      {count > 0 && (
        <ul className="max-h-36 min-h-0 space-y-1.5 overflow-y-auto rounded-xl bg-surface2 px-3 py-2.5 text-xs lg:px-3.5 lg:text-[13px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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

      {/* One row in English; a longer translation wraps to two rows instead of being cut. */}
      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" className="flex-auto" disabled={!isOpen || !draft.length} onClick={onUndo}>
          {labels.undo}
        </Button>
        <Button variant="ghost" className="flex-auto" disabled={!isOpen || !draft.length} onClick={onClear}>
          {labels.clear}
        </Button>
        <Button variant="ghost" className="flex-auto" disabled={!isOpen || !draft.length} onClick={onDouble}>
          {labels.double}
        </Button>
        <Button variant="ghost" className="flex-auto" disabled={!isOpen || pending} onClick={onRebet}>
          {labels.rebet}
        </Button>
      </div>

      <div className="flex items-baseline justify-between gap-3 text-xs lg:text-[13px]">
        <span className="text-muted">{settled ? labels.total_win : labels.total_bet}</span>
        <span className={`text-sm font-semibold tabular-nums lg:text-base ${paid && winCents ? 'text-lime' : ''}`}>
          {paid
            ? `${winCents ? '+' : ''}${formatBalance(fromCents(winCents))}`
            : formatBalance(fromCents(settled ? 0 : placedCents + draftCents))}{' '}
          {currency}
        </span>
      </div>

      <Button size="lg" block disabled={!isOpen || pending || !draft.length} suffix={buttonSuffix} onClick={onPlace}>
        {buttonLabel}
      </Button>

      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </Card>
  )
}
