import type { ReactNode } from 'react'

type Tone = 'lime' | 'cyan' | 'magenta' | 'muted'

const TONES: Record<Tone, string> = {
  lime: 'bg-lime/10 text-lime',
  cyan: 'bg-cyan/10 text-cyan',
  magenta: 'bg-magenta/10 text-magenta',
  muted: 'bg-surface2 text-muted',
}

interface BadgeProps {
  tone?: Tone
  small?: boolean // the BOT and YOU tags inside a table row
  dot?: boolean // the LIVE badge's dot
  className?: string
  children: ReactNode
}

// DEMO MODE, LIVE, soon, BOT, YOU: one shape, one line.
export default function Badge({ tone = 'muted', small = false, dot = false, className = '', children }: BadgeProps) {
  const shape = small
    ? 'gap-1 rounded-md px-1.5 py-0.5 text-[10px] leading-none'
    : 'gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold'

  return (
    <span className={`inline-flex shrink-0 items-center whitespace-nowrap ${shape} ${TONES[tone]} ${className}`}>
      {dot && <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  )
}
