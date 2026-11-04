'use client'

import { usePathname } from 'next/navigation'
import PageTitle from '@/components/ui/PageTitle'
import type { PageInfo } from '@/types/header'
import SearchBox from './SearchBox'

interface HeaderTitleProps {
  pages: Record<string, PageInfo>
  searchPlaceholder: string
}

// The left of the top bar: the lobby searches its games, every other page shows its name.
export default function HeaderTitle({ pages, searchPlaceholder }: HeaderTitleProps) {
  const pathname = usePathname()
  const title = pages[pathname]?.title

  return (
    // On a phone it is the second row, under the burger and the balance.
    <div className="order-last w-full min-w-0 lg:order-none lg:w-auto lg:flex-1">
      {pathname === '/' ? <SearchBox placeholder={searchPlaceholder} /> : title && <PageTitle>{title}</PageTitle>}
    </div>
  )
}
