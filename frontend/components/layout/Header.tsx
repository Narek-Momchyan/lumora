import Logo from '@/components/Logo'
import Badge from '@/components/ui/Badge'
import { formatBalance } from '@/lib/wallet'
import type { Player } from '@/types/account'
import type { HeaderLabels, Language, Logo as LogoData, PageInfo, SidebarItem } from '@/types/header'
import type { Wallet } from '@/types/wallet'
import AvatarMenu from './AvatarMenu'
import HeaderTitle from './HeaderTitle'
import MobileNav from './MobileNav'

interface HeaderProps {
  logo: LogoData | null
  items: SidebarItem[]
  pages: Record<string, PageInfo>
  labels: HeaderLabels
  wallet: Wallet | null
  me: Player | null
  languages: Language[] | null
  lang: string
}

// The top bar of every page: title or search on the left, demo badge, balance and account on the right.
export default function Header({ logo, items, pages, labels, wallet, me, languages, lang }: HeaderProps) {
  return (
    <header className="flex flex-wrap items-center gap-3 px-4 py-4 sm:px-6 lg:h-22 lg:flex-nowrap lg:gap-4 lg:px-10 lg:py-0">
      <MobileNav logo={logo} items={items} pages={pages} labels={labels} />
      <div className="min-w-0 lg:hidden">
        <Logo logo={logo} />
      </div>

      <HeaderTitle pages={pages} searchPlaceholder={labels.search_placeholder} />

      <div className="ml-auto flex shrink-0 items-center gap-3 lg:gap-4">
        <span className="hidden sm:block">
          <Badge tone="lime">{labels.demo_badge}</Badge>
        </span>

        {wallet && (
          <p
            aria-label={labels.balance_label}
            className="flex h-10 items-center gap-2 rounded-xl border border-accent bg-surface px-3 text-sm font-semibold whitespace-nowrap tabular-nums sm:px-4 lg:text-[15px]"
          >
            <span className="size-3.5 rounded-full bg-linear-to-r from-accent to-accent2" aria-hidden="true" />
            {formatBalance(wallet.balance)} {labels.currency}
          </p>
        )}

        <AvatarMenu
          name={me?.display_name || me?.email.split('@')[0]}
          languages={languages}
          lang={lang}
          labels={labels}
        />
      </div>
    </header>
  )
}
