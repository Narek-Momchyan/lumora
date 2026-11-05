'use client'

import { useState } from 'react'
import Card from '@/components/ui/Card'
import Chip from '@/components/ui/Chip'
import SectionTitle from '@/components/ui/SectionTitle'
import { fill, marketName, pickName } from '@/lib/sports'
import type { BetLabels, Market, MarketKind, Match, Selection, SportsUiLabels } from '@/types/sports'
import OddsCell from './OddsCell'

type Group = 'all' | 'main' | 'goals' | 'score'

const GROUP_OF: Record<MarketKind, Exclude<Group, 'all'>> = {
  '1x2': 'main',
  double_chance: 'main',
  btts: 'main',
  total: 'goals',
  correct_score: 'score',
}

interface MarketGridProps {
  match: Match
  markets: Market[]
  labels: SportsUiLabels
  bet: BetLabels
}

// Every market of a match (design 07) under the All / Main / Goals / Score chips.
export default function MarketGrid({ match, markets, labels, bet }: MarketGridProps) {
  const [group, setGroup] = useState<Group>('all')
  const visible = (kind: MarketKind) => group === 'all' || GROUP_OF[kind] === group
  const ofKind = (kind: MarketKind) => markets.filter((market) => market.kind === kind)
  const one = (kind: MarketKind) => ofKind(kind)[0]

  function cell(market: Market, selection: Selection, label?: string, stacked = false) {
    return (
      <OddsCell
        key={selection.id}
        selection={selection}
        match={match}
        kind={market.kind}
        line={market.line}
        code={selection.code}
        label={label}
        stacked={stacked}
        marketOpen={market.status === 'open'}
      />
    )
  }

  // 1X2, double chance and both teams to score: a row of labelled prices
  function row(market: Market | undefined, label: (code: string) => string, columns: string) {
    if (!market || !visible(market.kind)) return null
    return (
      <Card key={market.id} padding="md" className="space-y-3">
        <SectionTitle title={marketName(market.kind, bet)} />
        <div className={`grid gap-2 ${columns}`}>
          {market.selections.map((selection) => cell(market, selection, label(selection.code), true))}
        </div>
      </Card>
    )
  }

  const totals = ofKind('total')
  const scores = one('correct_score')
  const scoreColumns: [string, string[]][] = [
    [bet.home, ['1-0', '2-0', '2-1', '3-0', '3-1', '3-2']],
    [bet.draw, ['0-0', '1-1', '2-2', '3-3', 'other']],
    [bet.away, ['0-1', '0-2', '1-2', '0-3', '1-3', '2-3']],
  ]

  const names = (code: string) => pickName('1x2', null, code, match, bet)
  const bestScore = scores ? Math.max(...scores.selections.map((selection) => Number(selection.odds))) : 0
  const count = markets.length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {(['all', 'main', 'goals', 'score'] as Group[]).map((id) => (
          <Chip key={id} active={group === id} onClick={() => setGroup(id)}>
            {
              labels[
                `${id === 'all' ? 'all' : id}_markets` as
                  'all_markets' | 'main_markets' | 'goals_markets' | 'score_markets'
              ]
            }
          </Chip>
        ))}
        <p className="ml-auto text-xs text-muted">{fill(labels.markets_total, { count })}</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-4">
          {row(one('1x2'), names, 'grid-cols-3')}
          {row(one('double_chance'), (code) => code, 'grid-cols-3')}
          {row(one('btts'), (code) => pickName('btts', null, code, match, bet), 'grid-cols-2')}
        </div>

        {visible('total') && totals.length > 0 && (
          <Card padding="md" className="space-y-3 self-start">
            <SectionTitle title={marketName('total', bet)} aside={`${labels.over_short} / ${labels.under_short}`} />
            <div className="grid grid-cols-[2.5rem_1fr_1fr] items-center gap-2">
              <span />
              <span className="text-center text-[11px] tracking-wide text-muted uppercase">{labels.over_short}</span>
              <span className="text-center text-[11px] tracking-wide text-muted uppercase">{labels.under_short}</span>
              {totals.map((market) => (
                <TotalRow key={market.id} market={market} cell={cell} />
              ))}
            </div>
          </Card>
        )}
      </div>

      {visible('correct_score') && scores && (
        <Card padding="md" className="space-y-3">
          <SectionTitle
            title={marketName('correct_score', bet)}
            aside={fill(labels.pays_up_to, { odds: Math.round(bestScore) })}
          />
          <div className="grid gap-4 sm:grid-cols-3">
            {scoreColumns.map(([title, codes]) => (
              <div key={title} className="space-y-2">
                <p className="text-[11px] tracking-wide text-muted uppercase">{title}</p>
                {codes.map((code) => {
                  const selection = scores.selections.find((row) => row.code === code)
                  return selection ? cell(scores, selection, pickName('correct_score', null, code, match, bet)) : null
                })}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function TotalRow({
  market,
  cell,
}: {
  market: Market
  cell: (market: Market, selection: Selection, label?: string) => React.ReactNode
}) {
  const over = market.selections.find((selection) => selection.code === 'over')
  const under = market.selections.find((selection) => selection.code === 'under')
  return (
    <>
      <span className="text-sm text-muted tabular-nums">{market.line}</span>
      {over ? cell(market, over) : <span />}
      {under ? cell(market, under) : <span />}
    </>
  )
}
