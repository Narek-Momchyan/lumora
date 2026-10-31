'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import type { Game, GameCategory, LobbyPageLabels } from '@/types/game'

interface GameFiltersProps {
  games: Game[]
  categories: GameCategory[]
  labels: LobbyPageLabels
}

const CHIP = 'rounded-full border px-4 py-2 text-sm whitespace-nowrap transition-colors'

export default function GameFilters({ games, categories, labels }: GameFiltersProps) {
  const searchParams = useSearchParams()
  const current = searchParams.get('category')

  function href(code: string | null) {
    const params = new URLSearchParams(searchParams)
    if (code) params.set('category', code)
    else params.delete('category')
    return params.size > 0 ? `/?${params}` : '/'
  }

  function chipClass(active: boolean) {
    return `${CHIP} ${active ? 'border-text bg-text text-bg' : 'border-border text-muted hover:text-text'}`
  }

  // A filter without games is useless, unless it announces a coming category.
  const visible = categories.filter(({ code, is_soon }) => is_soon || games.some((game) => game.category === code))

  return (
    <nav aria-label={labels.filters_label} className="flex gap-2 overflow-x-auto pb-1">
      <Link href={href(null)} scroll={false} className={chipClass(current === null)}>
        {labels.filter_all}
      </Link>

      {visible.map(({ id, code, filter_label, is_soon }) =>
        is_soon ? (
          <span key={id} className={`${CHIP} border-border text-muted`}>
            {filter_label} · {labels.soon_badge}
          </span>
        ) : (
          <Link key={id} href={href(code)} scroll={false} className={chipClass(current === code)}>
            {filter_label}
          </Link>
        ),
      )}
    </nav>
  )
}
