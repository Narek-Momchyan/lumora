'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useSearchParams } from 'next/navigation'
import { Fragment } from 'react'
import Badge from '@/components/ui/Badge'
import { LOBBY_PATH } from '@/lib/games'
import type { HeaderLabels, PageInfo, SidebarItem } from '@/types/header'
import { useMode } from './ModeProvider'

interface SidebarNavProps {
  items: SidebarItem[]
  pages: Record<string, PageInfo>
  labels: HeaderLabels
  onNavigate?: () => void // the mobile drawer closes itself
}

const ROW = 'flex items-center gap-2 rounded-xl py-2.5 pr-2 pl-2.5 text-[15px] whitespace-nowrap text-text transition-colors'

function Marker({ item, active }: { item: SidebarItem; active: boolean }) {
  // An icon or a flag from the admin; without one, the design's small dot.
  if (item.icon) {
    return <Image src={item.icon} alt="" width={20} height={20} unoptimized className="size-5 shrink-0 object-contain" />
  }
  return <span className={`mx-[7px] size-1.5 shrink-0 rounded-full ${active ? 'bg-accent' : 'bg-border'}`} aria-hidden="true" />
}

// The site's only navigation: the current section's items (Sports or Casino), the same on every
// page and in the mobile drawer.
export default function SidebarNav({ items, pages, labels, onNavigate }: SidebarNavProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const mode = useMode()

  // The lobby's filter, or the category of the game whose page is open.
  const category = pathname === LOBBY_PATH ? searchParams.get('category') : (pages[pathname]?.category ?? null)
  const groupTitles = { leagues: labels.leagues_group, my: labels.my_lumora_group }

  function isActive(item: SidebarItem) {
    if (item.category) return item.category === category
    if (item.url === LOBBY_PATH) return pathname === LOBBY_PATH && !category
    return item.url === pathname
  }

  const shown = items.filter((item) => item.mode === mode)

  return (
    <nav aria-label={labels.navigation_label} className="space-y-1">
      {shown.map((item, index) => {
        const active = isActive(item)
        const startsGroup = item.group !== '' && item.group !== shown[index - 1]?.group
        const heading = startsGroup && (
          <p className="truncate px-3 pt-5 pb-1.5 text-[11px] font-semibold tracking-widest text-muted uppercase">
            {groupTitles[item.group as 'leagues' | 'my']}
          </p>
        )

        if (item.is_soon) {
          return (
            <Fragment key={item.id}>
              {heading}
              <span aria-disabled="true" className={`${ROW} cursor-default`}>
                <Marker item={item} active={false} />
                <span className="min-w-0 truncate" title={item.title}>
                  {item.title}
                </span>
                <Badge small className="ml-auto">
                  {labels.soon_label}
                </Badge>
              </span>
            </Fragment>
          )
        }

        return (
          <Fragment key={item.id}>
            {heading}
            <Link
              href={item.url}
              onClick={onNavigate}
              aria-current={active ? 'page' : undefined}
              className={`${ROW} ${active ? 'bg-surface2 shadow-[inset_2px_0_0_var(--color-accent)]' : 'hover:bg-surface2/60'}`}
            >
              <Marker item={item} active={active} />
              <span className="min-w-0 truncate">{item.title}</span>
            </Link>
          </Fragment>
        )
      })}
    </nav>
  )
}
