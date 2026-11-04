interface OddsButtonProps {
  label?: string // "1 · Bayern", "Draw", "Over 2.5"; a table cell has none
  odds: string // always a string with two decimals from the API, never a float
  selected?: boolean // in the bet slip
  disabled?: boolean // the market is closed (kickoff)
  onClick?: () => void
}

// One price of a market (designs 06, 07). Picked: lime with dark text and a glow, in both themes.
export default function OddsButton({ label, odds, selected = false, disabled = false, onClick }: OddsButtonProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      disabled={disabled}
      onClick={onClick}
      className={`flex h-11 min-w-0 items-center gap-2 rounded-xl border px-3 text-sm transition disabled:cursor-not-allowed disabled:opacity-40 ${
        label ? 'justify-between' : 'justify-center'
      } ${
        selected
          ? 'border-lime bg-lime text-bg shadow-lg shadow-lime/30'
          : 'border-border bg-surface2 text-text hover:enabled:border-accent/60'
      }`}
    >
      {label && <span className={`min-w-0 truncate ${selected ? 'text-bg/80' : 'text-muted'}`}>{label}</span>}
      <span className="shrink-0 font-heading text-base font-bold tabular-nums">{odds}</span>
    </button>
  )
}
