import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  // A closed or waiting action looks like the design's "Bets closed" button, not a faded gradient.
  primary:
    'bg-linear-to-r from-cyan to-magenta font-semibold text-bg shadow-lg shadow-cyan/10 hover:enabled:opacity-90 disabled:border disabled:border-border disabled:from-surface2 disabled:to-surface2 disabled:text-muted disabled:shadow-none',
  ghost: 'border border-border bg-surface2 font-medium text-text hover:enabled:border-cyan/60 disabled:opacity-40',
}

const SIZES: Record<Size, string> = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-10 px-3 text-sm',
  lg: 'h-11 px-5 text-[15px]',
}

interface ButtonStyle {
  variant?: Variant
  size?: Size
  block?: boolean // full width
}

// For a Link that looks like a button.
export function buttonClass({ variant = 'primary', size = 'md', block = false }: ButtonStyle = {}) {
  return `inline-flex min-w-0 items-center justify-center gap-1.5 rounded-xl whitespace-nowrap transition disabled:cursor-not-allowed ${
    VARIANTS[variant]
  } ${SIZES[size]} ${block ? 'w-full' : ''}`
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  ButtonStyle & {
    suffix?: ReactNode // never cut, e.g. the amount after "Place bets ·"
  }

export default function Button({
  variant,
  size,
  block,
  type = 'button',
  className = '',
  children,
  suffix,
  ...props
}: ButtonProps) {
  return (
    <button type={type} className={`${buttonClass({ variant, size, block })} ${className}`} {...props}>
      {/* A long translation is cut with "…" instead of breaking the button into two lines. */}
      <span className="truncate">{children}</span>
      {suffix && <span className="shrink-0">{suffix}</span>}
    </button>
  )
}
