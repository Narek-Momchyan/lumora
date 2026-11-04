import Image from 'next/image'
import Link from 'next/link'
import Badge from '@/components/ui/Badge'
import { cardClass } from '@/components/ui/Card'
import { GAME_ROUTES } from '@/lib/games'
import type { Game, LobbyPageLabels } from '@/types/game'

interface GameCardProps {
  game: Game
  categoryLabel: string
  labels: LobbyPageLabels
}

export default function GameCard({ game, categoryLabel, labels }: GameCardProps) {
  const rtp = `${labels.rtp_label} ${Number(game.rtp).toFixed(1)}%`

  const card = (
    <>
      <div className="relative aspect-[3/2] bg-linear-to-br from-magenta/40 via-surface2 to-cyan">
        {game.image && <Image src={game.image} alt="" fill unoptimized className="object-cover object-top" />}
        {!game.is_playable && (
          <span className="absolute top-3 right-3">
            <Badge tone="lime">{labels.soon_badge}</Badge>
          </span>
        )}
      </div>

      <div className="px-4 py-3.5">
        <h3 className="truncate font-heading text-base font-bold lg:text-[17px]">{game.title}</h3>
        <p className="mt-1 truncate text-xs text-muted">
          {rtp} · {categoryLabel}
        </p>
      </div>
    </>
  )

  const route = game.is_playable ? GAME_ROUTES[game.slug] : undefined
  const frame = `block overflow-hidden ${cardClass({ padding: 'none' })}`

  return route ? (
    <Link href={route} className={`${frame} transition-colors hover:border-cyan`}>
      {card}
    </Link>
  ) : (
    <article className={frame}>{card}</article>
  )
}
