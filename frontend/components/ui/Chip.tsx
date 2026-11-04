import Link from 'next/link'
import type { ReactNode } from 'react'

const BASE = 'inline-flex h-9 shrink-0 items-center rounded-full border px-4 text-sm whitespace-nowrap transition-colors'
const ACTIVE = 'border-text bg-text font-semibold text-bg'
const IDLE = 'border-border text-muted hover:border-muted hover:text-text'

interface ChipProps {
  active?: boolean
  href?: string // a filter that lives in the URL
  onClick?: () => void
  children: ReactNode
}

// A pill filter: Today / Tomorrow, All markets / Main / Goals (designs 06, 07).
export default function Chip({ active = false, href, onClick, children }: ChipProps) {
  const className = `${BASE} ${active ? ACTIVE : IDLE}`

  if (href) {
    return (
      <Link href={href} scroll={false} aria-current={active ? 'true' : undefined} className={className}>
        {children}
      </Link>
    )
  }
  return (
    <button type="button" aria-pressed={active} onClick={onClick} className={className}>
      {children}
    </button>
  )
}
