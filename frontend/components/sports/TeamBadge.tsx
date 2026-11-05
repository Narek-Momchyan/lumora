'use client'

import { useState } from 'react'
import type { Team } from '@/types/sports'

const SIZES = { sm: 'size-5 text-[7px]', md: 'size-7 text-[9px]', lg: 'size-10 text-xs', xl: 'size-20 text-xl' }

interface TeamBadgeProps {
  team: Pick<Team, 'tla' | 'name' | 'color' | 'text_color' | 'crest'>
  size?: keyof typeof SIZES
}

// The club's crest (football-data.org's, replaceable in the admin). While it is missing or fails to
// load, the club's initials in its colours. Those two colours are the only values that come from
// the API instead of the tokens: every club has its own.
export default function TeamBadge({ team, size = 'md' }: TeamBadgeProps) {
  const [failed, setFailed] = useState(false)

  if (team.crest && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- a crest is a small remote image, often an SVG
      <img
        src={team.crest}
        alt=""
        onError={() => setFailed(true)}
        className={`${SIZES[size].split(' ')[0]} shrink-0 object-contain`}
      />
    )
  }

  return (
    <span
      aria-hidden="true"
      style={{ backgroundColor: team.color, color: team.text_color }}
      className={`${SIZES[size]} flex shrink-0 items-center justify-center rounded-full font-bold tracking-tight`}
    >
      {team.tla.slice(0, 3)}
    </span>
  )
}
