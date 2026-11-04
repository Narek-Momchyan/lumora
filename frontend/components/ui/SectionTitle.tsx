import type { ReactNode } from 'react'

interface SectionTitleProps {
  title: string
  aside?: ReactNode // the small grey text on the right: "148 players", "Round #18 204"
  large?: boolean // a section of the page ("Popular now"), not the title of a card
}

export default function SectionTitle({ title, aside, large = false }: SectionTitleProps) {
  return (
    <div className="flex min-w-0 items-baseline justify-between gap-3">
      <h2 className={`truncate font-heading font-bold ${large ? 'text-xl' : 'text-base lg:text-lg'}`}>{title}</h2>
      {aside && <p className="shrink-0 text-xs text-muted">{aside}</p>}
    </div>
  )
}
