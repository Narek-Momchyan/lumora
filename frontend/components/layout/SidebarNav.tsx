'use client'

import Link from 'next/link'
import { usePathname, useSearchParams } from 'next/navigation'
import Badge from '@/components/ui/Badge'
import type { HeaderLabels, PageInfo, SidebarItem } from '@/types/header'

interface SidebarNavProps {
  items: SidebarItem[]
  pages: Record<string, PageInfo>
  labels: HeaderLabels
  onNavigate?: () => void // the mobile drawer closes itself
}

const ROW = 'flex items-center gap-2.5 rounded-xl py-2.5 pr-2 pl-3 text-[15px] whitespace-nowrap text-text transition-colors'

function Dot({ active }: { active: boolean }) {
  return <span className={`size-1.5 shrink-0 rounded-full ${active ? 'bg-cyan' : 'bg-border'}`} aria-hidden="true" />
}

// The site's only navigation, the same on every page and in the mobile drawer.
export default function SidebarNav({ items, pages, labels, onNavigate }: SidebarNavProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  // The lobby's filter, or the category of the game whose page is open.
  const category = pathname === '/' ? searchParams.get('category') : (pages[pathname]?.category ?? null)

  function isActive(item: SidebarItem) {
    if (item.category) return item.category === category
    if (item.url === '/') return pathname === '/' && !category
    return item.url === pathname
  }

  return (
    <nav aria-label={labels.navigation_label} className="space-y-1">
      {items.map((item) => {
        const active = isActive(item)

        if (item.is_soon) {
          return (
            <span key={item.id} aria-disabled="true" className={`${ROW} cursor-default`}>
              <Dot active={false} />
              <span className="min-w-0 truncate">{item.title}</span>
              <Badge small className="ml-auto">
                {labels.soon_label}
              </Badge>
            </span>
          )
        }

        return (
          <Link
            key={item.id}
            href={item.url}
            onClick={onNavigate}
            aria-current={active ? 'page' : undefined}
            className={`${ROW} ${active ? 'bg-surface2' : 'hover:bg-surface2/60'}`}
          >
            <Dot active={active} />
            <span className="min-w-0 truncate">{item.title}</span>
          </Link>
        )
      })}
    </nav>
  )
}
