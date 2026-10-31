import Image from 'next/image'
import Link from 'next/link'
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
      <div className="relative aspect-video bg-linear-to-br from-magenta/40 via-surface2 to-cyan">
        {game.image && <Image src={game.image} alt="" fill unoptimized className="object-cover object-top" />}
        {!game.is_playable && (
          <span className="absolute top-3 right-3 rounded-full bg-bg/80 px-3 py-1 text-xs font-semibold text-lime">
            {labels.soon_badge}
          </span>
        )}
      </div>

      <div className="p-4">
        <h3 className="truncate font-heading font-bold">{game.title}</h3>
        <p className="mt-1 truncate text-xs text-muted">
          {rtp} · {categoryLabel}
        </p>
      </div>
    </>
  )

  const route = game.is_playable ? GAME_ROUTES[game.slug] : undefined
  const frame = 'block overflow-hidden rounded-2xl border border-border bg-surface'

  return route ? (
    <Link href={route} className={`${frame} transition-colors hover:border-cyan`}>
      {card}
    </Link>
  ) : (
    <article className={frame}>{card}</article>
  )
}
