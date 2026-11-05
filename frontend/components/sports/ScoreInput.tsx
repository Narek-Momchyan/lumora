'use client'

interface ScoreInputProps {
  value: string
  onChange: (value: string) => void
  label: string // for screen readers: "Everton goals"
  disabled?: boolean
}

// One box of a score prediction. Digits only, at most two (the backend allows 0-20). The focused
// box glows in the lime of the "night stadium" theme.
export default function ScoreInput({ value, onChange, label, disabled = false }: ScoreInputProps) {
  return (
    <input
      type="text"
      inputMode="numeric"
      autoComplete="off"
      maxLength={2}
      value={value}
      disabled={disabled}
      aria-label={label}
      placeholder="–"
      onChange={(event) => onChange(event.target.value.replace(/\D/g, '').slice(0, 2))}
      onFocus={(event) => event.target.select()}
      className="size-11 rounded-xl border border-border bg-surface2 text-center font-heading text-lg font-bold tabular-nums transition-shadow outline-none placeholder:text-muted/50 focus:border-lime focus:shadow-lg focus:shadow-lime/30 disabled:cursor-not-allowed disabled:opacity-60 sm:size-12"
    />
  )
}
