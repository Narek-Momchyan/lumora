import Logo from '@/components/Logo'
import { formatBalance } from '@/lib/wallet'
import type { Player } from '@/types/account'
import type { HeaderLabels, Language, Logo as LogoData } from '@/types/header'
import type { Wallet } from '@/types/wallet'
import AvatarMenu from './AvatarMenu'
import SearchBox from './SearchBox'

interface HeaderProps {
  logo: LogoData | null
  labels: HeaderLabels
  wallet: Wallet | null
  me: Player | null
  languages: Language[] | null
  lang: string
}

export default function Header({ logo, labels, wallet, me, languages, lang }: HeaderProps) {
  return (
    <header className="flex flex-wrap items-center gap-3 px-4 py-5 sm:px-6 lg:flex-nowrap lg:px-10">
      <div className="lg:hidden">
        <Logo logo={logo} />
      </div>

      <SearchBox placeholder={labels.search_placeholder} />

      <div className="ml-auto flex items-center gap-3">
        <span className="hidden rounded-full bg-lime/10 px-3 py-1.5 text-xs font-semibold whitespace-nowrap text-lime sm:inline">
          {labels.demo_badge}
        </span>

        {wallet && (
          <p
            aria-label={labels.balance_label}
            className="flex items-center gap-2 rounded-xl border border-cyan bg-surface px-3 py-2 text-sm font-semibold whitespace-nowrap"
          >
            <span className="size-3.5 rounded-full bg-linear-to-r from-cyan to-magenta" aria-hidden="true" />
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
