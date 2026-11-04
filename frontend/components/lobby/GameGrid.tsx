'use client'

import { useSearchParams } from 'next/navigation'
import SectionTitle from '@/components/ui/SectionTitle'
import type { Game, GameCategory, LobbyPageLabels } from '@/types/game'
import GameCard from './GameCard'

interface GameGridProps {
  games: Game[]
  categories: GameCategory[]
  labels: LobbyPageLabels
}

export default function GameGrid({ games, categories, labels }: GameGridProps) {
  const searchParams = useSearchParams()
  const category = searchParams.get('category')
  const query = (searchParams.get('q') ?? '').trim().toLowerCase()

  const cardLabel = (code: string) => categories.find((item) => item.code === code)?.card_label ?? ''

  const matches = games.filter(
    (game) =>
      (!category || game.category === category) &&
      (!query || game.title.toLowerCase().includes(query) || cardLabel(game.category).toLowerCase().includes(query)),
  )

  // The sidebar's category opens the lobby filtered: the section is named after it.
  const categoryTitle = categories.find((item) => item.code === category)?.filter_label

  const sections =
    category || query
      ? [{ title: categoryTitle ?? labels.section_all, games: matches }]
      : [
          { title: labels.section_popular, games: matches.filter((game) => game.is_featured) },
          { title: labels.section_all, games: matches.filter((game) => !game.is_featured) },
        ]

  if (matches.length === 0) return <p className="text-sm text-muted">{labels.no_results}</p>

  return (
    <div className="space-y-8">
      {sections
        .filter((section) => section.games.length > 0)
        .map((section) => (
          <section key={section.title}>
            <SectionTitle title={section.title} large />
            <div className="mt-4 grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-5">
              {section.games.map((game) => (
                <GameCard key={game.id} game={game} categoryLabel={cardLabel(game.category)} labels={labels} />
              ))}
            </div>
          </section>
        ))}
    </div>
  )
}
