import Card from '@/components/ui/Card'
import { teamName } from '@/lib/sports'
import type { PredictionLabels, StandingRow, StandingZone, ZoneKind } from '@/types/predictions'
import type { SportsUiLabels } from '@/types/sports'
import FormDots from './FormDots'
import TeamBadge from './TeamBadge'

const ZONE_BAR: Record<ZoneKind, string> = {
  champions_league: 'bg-lime',
  europa_league: 'bg-accent2',
  conference_league: 'bg-accent2/50',
  playoff: 'bg-muted',
  relegation: 'bg-danger',
}

interface LeagueTableProps {
  rows: StandingRow[]
  zones: StandingZone[]
  labels: PredictionLabels
  ui: Pick<SportsUiLabels, 'form_win' | 'form_draw' | 'form_loss'>
}

function zoneOf(zones: StandingZone[], position: number) {
  return zones.find((zone) => position >= zone.from_position && position <= zone.to_position)
}

// The league table (design 10): position, club, played / won / drawn / lost, goals, goal difference,
// points and the last 5 results. A coloured bar on the left marks the zones set in the admin.
// The form string is oldest first; it is shown newest first like everywhere else.
export default function LeagueTable({ rows, zones, labels, ui }: LeagueTableProps) {
  const groups = new Map<string, StandingRow[]>()
  for (const row of rows) groups.set(`${row.stage}|${row.group}`, [...(groups.get(`${row.stage}|${row.group}`) ?? []), row])
  const used = [...new Set(rows.map((row) => zoneOf(zones, row.position)?.kind).filter(Boolean))] as ZoneKind[]
  const legend: Record<ZoneKind, string> = {
    champions_league: labels.zone_champions_league,
    europa_league: labels.zone_europa_league,
    conference_league: labels.zone_conference_league,
    playoff: labels.zone_playoff,
    relegation: labels.zone_relegation,
  }
  const head = 'py-3 text-center text-[11px] font-medium tracking-wide text-muted uppercase'

  return (
    <Card padding="none" className="overflow-hidden">
      {[...groups.entries()].map(([key, group]) => (
        <div key={key} className="overflow-x-auto">
          {groups.size > 1 && (
            <h3 className="px-4 pt-3 font-heading text-sm font-bold">{group[0].group || group[0].stage}</h3>
          )}
          <table className="w-full min-w-[20rem] border-collapse text-sm">
            <thead>
              <tr>
                <th className={`${head} w-10 pl-4`}>#</th>
                <th className={`${head} text-left`}>{labels.col_club}</th>
                <th className={`${head} w-9`}>{labels.col_played}</th>
                <th className={`${head} hidden w-9 sm:table-cell`}>{labels.col_won}</th>
                <th className={`${head} hidden w-9 sm:table-cell`}>{labels.col_draw}</th>
                <th className={`${head} hidden w-9 sm:table-cell`}>{labels.col_lost}</th>
                <th className={`${head} hidden w-16 md:table-cell`}>{labels.col_goals}</th>
                <th className={`${head} w-10`}>{labels.col_diff}</th>
                <th className={`${head} w-10`}>{labels.col_points}</th>
                <th className={`${head} hidden w-36 pr-4 lg:table-cell`}>{labels.col_form}</th>
              </tr>
            </thead>
            <tbody>
              {group.map((row) => {
                const zone = zoneOf(zones, row.position)
                const diff = row.goal_difference
                return (
                  <tr key={row.id} className="border-t border-border">
                    <td className="relative py-2.5 pl-4 text-center text-xs text-muted tabular-nums">
                      {zone && (
                        <span aria-hidden="true" className={`absolute inset-y-1 left-0 w-[3px] rounded-r ${ZONE_BAR[zone.kind]}`} />
                      )}
                      {row.position}
                    </td>
                    <td className="py-2.5">
                      <span className="flex min-w-0 items-center gap-2">
                        <TeamBadge team={row.team} size="md" />
                        <span className="truncate">{teamName(row.team)}</span>
                      </span>
                    </td>
                    <td className="text-center tabular-nums">{row.played}</td>
                    <td className="hidden text-center tabular-nums sm:table-cell">{row.won}</td>
                    <td className="hidden text-center tabular-nums sm:table-cell">{row.draw}</td>
                    <td className="hidden text-center tabular-nums sm:table-cell">{row.lost}</td>
                    <td className="hidden text-center tabular-nums md:table-cell">
                      {row.goals_for}:{row.goals_against}
                    </td>
                    <td
                      className={`text-center tabular-nums ${diff > 0 ? 'text-lime' : diff < 0 ? 'text-danger' : 'text-muted'}`}
                    >
                      {diff > 0 ? `+${diff}` : diff}
                    </td>
                    <td className="text-center font-heading font-bold tabular-nums">{row.points}</td>
                    <td className="hidden pr-4 text-center lg:table-cell">
                      <FormDots form={row.form ? row.form.split(',').filter(Boolean).reverse() : []} labels={ui} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ))}

      {used.length > 0 && (
        <ul className="flex flex-wrap gap-x-5 gap-y-2 border-t border-border px-4 py-3 text-xs text-muted">
          {used.map((kind) => (
            <li key={kind} className="flex items-center gap-2">
              <span aria-hidden="true" className={`size-2.5 rounded-sm ${ZONE_BAR[kind]}`} />
              {legend[kind]}
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
