import Logo from '@/components/Logo'
import type { Game } from '@/types/game'

function rtpRange(games: Game[]) {
  const rtps = games.map((game) => Number(game.rtp))
  const low = Math.min(...rtps)
  const high = Math.max(...rtps)
  return low === high ? `${low}%` : `${low}–${high}%`
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <dd className="font-heading text-2xl font-bold text-cyan">{value}</dd>
      <dt className="mt-1 text-xs text-muted">{label}</dt>
    </div>
  )
}

// `games` is null or empty when the API can't be reached: those stats are left out.
export default function LoginHero({ games }: { games: Game[] | null }) {
  return (
    <section className="flex flex-col px-6 py-8 lg:px-16 lg:py-12">
      <Logo />

      <div className="flex flex-1 flex-col justify-center pt-12 lg:pt-0">
        <h1 className="font-heading text-4xl leading-tight font-bold sm:text-6xl sm:leading-tight">
          Play bold.
          <br />
          Risk nothing.
        </h1>
        <p className="mt-6 max-w-md text-muted">
          Slots, crash and table games with demo coins only. No deposits, no real money, just the
          thrill.
        </p>

        <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-4">
          {games && games.length > 0 && (
            <>
              <Stat value={String(games.length)} label="Games" />
              <Stat value={rtpRange(games)} label="RTP" />
            </>
          )}
          <Stat value="0" label="Real money" />
        </dl>
      </div>
    </section>
  )
}
