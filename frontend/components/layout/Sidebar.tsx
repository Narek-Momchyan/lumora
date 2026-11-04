import Logo from '@/components/Logo'
import type { HeaderLabels, Logo as LogoData, PageInfo, SidebarItem } from '@/types/header'
import SidebarNav from './SidebarNav'

interface SidebarProps {
  logo: LogoData | null
  items: SidebarItem[]
  pages: Record<string, PageInfo>
  labels: HeaderLabels
}

// From lg up. Below it the same SidebarNav opens from the header's burger (MobileNav).
export default function Sidebar({ logo, items, pages, labels }: SidebarProps) {
  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col overflow-y-auto border-r border-border bg-surface px-3 py-7 lg:flex">
      <div className="px-1">
        <Logo logo={logo} />
      </div>
      <div className="mt-10">
        <SidebarNav items={items} pages={pages} labels={labels} />
      </div>
    </aside>
  )
}
