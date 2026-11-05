import type { Metadata } from 'next'
import { connection } from 'next/server'
import Card from '@/components/ui/Card'
import Chip from '@/components/ui/Chip'
import BetSlip from '@/components/sports/BetSlip'
import BetTicket from '@/components/sports/BetTicket'
import ProfitChart from '@/components/sports/ProfitChart'
import {
  getBetLabels,
  getBetSummary,
  getBets,
  getHeaderLabels,
  getSidebarItems,
  getSportsUiLabels,
} from '@/lib/content'
import { displayLang } from '@/lib/lang'
import { fill } from '@/lib/sports'
import { formatBalance } from '@/lib/wallet'

const TABS = ['', 'open', 'settled'] as const

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const items = await getSidebarItems(await displayLang())
  return { title: items?.find((item) => item.url === '/my-bets')?.title }
}

// My bets (design 08): the week's totals, my tickets by status and the profit of each day.
export default async function MyBetsPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const lang = await displayLang()
  const { status = '' } = await searchParams
  const tab = TABS.includes(status as (typeof TABS)[number]) ? status : ''

  const [ui, names, header, summary, bets] = await Promise.all([
    getSportsUiLabels(lang),
    getBetLabels(lang),
    getHeaderLabels(lang),
    getBetSummary(),
    getBets(tab, lang),
  ])
  const currency = header.currency
  const open = summary?.open ?? 0

  const tabs = [
    { id: '', label: ui.tab_all },
    { id: 'open', label: open > 0 ? `${ui.tab_open} · ${open}` : ui.tab_open },
    { id: 'settled', label: ui.tab_settled },
  ]

  const profit = Number(summary?.profit ?? 0)
  const stats = summary
    ? [
        { label: ui.staked, value: `${formatBalance(summary.staked)} ${currency}`, tone: '' },
        { label: ui.returned, value: `${formatBalance(summary.returned)} ${currency}`, tone: '' },
        {
          label: ui.profit,
          value: `${profit > 0 ? '+' : ''}${formatBalance(summary.profit)} ${currency}`,
          tone: profit > 0 ? 'text-lime' : profit < 0 ? 'text-danger' : '',
        },
        { label: ui.won_bets, value: fill(ui.won_of, { won: summary.won, total: summary.bets }), tone: '' },
      ]
    : []

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22.5rem]">
      <div className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {tabs.map(({ id, label }) => (
            <Chip key={id} href={id ? `/my-bets?status=${id}` : '/my-bets'} active={tab === id}>
              {label}
            </Chip>
          ))}
          <span className="ml-auto text-xs text-muted">{ui.this_week}</span>
        </div>

        {stats.length > 0 && (
          <dl className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            {stats.map(({ label, value, tone }) => (
              <Card key={label} as="div" padding="md" className="min-w-0">
                <dt className="truncate text-xs text-muted">{label}</dt>
                <dd className={`mt-1 truncate font-heading text-lg font-bold tabular-nums ${tone}`}>{value}</dd>
              </Card>
            ))}
          </dl>
        )}

        {(bets ?? []).length === 0 ? (
          <p className="text-sm text-muted">{ui.empty_my_bets}</p>
        ) : (
          <div className="space-y-4">
            {bets!.map((bet) => (
              <BetTicket key={bet.id} bet={bet} labels={ui} names={names} currency={currency} />
            ))}
          </div>
        )}
      </div>

      <aside className="min-w-0 space-y-6">
        <BetSlip />
        {summary && <ProfitChart days={summary.by_day} labels={ui} />}
      </aside>
    </div>
  )
}
