import Logo from '@/components/Logo'
import type { LoginPageLabels } from '@/types/account'
import type { Game } from '@/types/game'
import type { Logo as LogoData } from '@/types/header'

function rtpRange(games: Game[]) {
  const rtps = games.map((game) => Number(game.rtp))
  const low = Math.min(...rtps)
  const high = Math.max(...rtps)
  return low === high ? `${low}%` : `${low}–${high}%`
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <dd className="font-heading text-2xl font-bold text-accent">{value}</dd>
      <dt className="mt-1 text-xs text-muted">{label}</dt>
    </div>
  )
}

interface LoginHeroProps {
  logo: LogoData | null
  // null or empty when the API can't be reached: those stats are left out.
  games: Game[] | null
  labels: LoginPageLabels
}

export default function LoginHero({ logo, games, labels }: LoginHeroProps) {
  return (
    <section className="flex flex-col px-6 py-8 lg:px-16 lg:py-12">
      <Logo logo={logo} />

      <div className="flex flex-1 flex-col justify-center pt-12 lg:pt-0">
        <h1 className="font-heading text-4xl leading-tight font-bold sm:text-6xl sm:leading-tight">
          {labels.hero_title_line_1}
          <br />
          {labels.hero_title_line_2}
        </h1>
        <p className="mt-6 max-w-md text-muted">{labels.hero_text}</p>

        <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-4">
          {games && games.length > 0 && (
            <>
              <Stat value={String(games.length)} label={labels.stat_games} />
              <Stat value={rtpRange(games)} label={labels.stat_rtp} />
            </>
          )}
          <Stat value="0" label={labels.stat_real_money} />
        </dl>
      </div>
    </section>
  )
}
