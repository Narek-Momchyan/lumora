'use client'

import Link from 'next/link'
import { usePathname, useSearchParams } from 'next/navigation'
import Logo from '@/components/Logo'
import type { HeaderLabels, Logo as LogoData, SidebarItem } from '@/types/header'

interface SidebarProps {
  logo: LogoData | null
  items: SidebarItem[]
  labels: HeaderLabels
}

function Dot({ active }: { active: boolean }) {
  return <span className={`size-1.5 rounded-full ${active ? 'bg-cyan' : 'bg-border'}`} aria-hidden="true" />
}

export default function Sidebar({ logo, items, labels }: SidebarProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  function isActive(url: string) {
    const [path, query] = url.split('?')
    return path === pathname && new URLSearchParams(query).get('category') === searchParams.get('category')
  }

  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border bg-surface px-4 py-8 lg:flex">
      <Logo logo={logo} />

      <nav aria-label={labels.navigation_label} className="mt-10 space-y-1">
        {items.map(({ id, title, url, is_soon }) =>
          is_soon ? (
            <span key={id} className="flex items-center gap-3 px-4 py-3 text-sm text-muted">
              <Dot active={false} />
              {title} ({labels.soon_label})
            </span>
          ) : (
            <Link
              key={id}
              href={url}
              aria-current={isActive(url) ? 'page' : undefined}
              className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition-colors hover:text-text ${
                isActive(url) ? 'bg-surface2 text-text' : 'text-muted'
              }`}
            >
              <Dot active={isActive(url)} />
              {title}
            </Link>
          ),
        )}
      </nav>
    </aside>
  )
}
