import type { ReactNode } from 'react'
import Header from '@/components/layout/Header'
import ModeProvider from '@/components/layout/ModeProvider'
import Sidebar from '@/components/layout/Sidebar'
import SportsBackdrop from '@/components/layout/SportsBackdrop'
import { getGames, getHeaderLabels, getLanguages, getLogo, getMe, getSidebarItems, getWallet } from '@/lib/content'
import { displayMode } from '@/lib/display-mode'
import { pagesByPath } from '@/lib/games'
import { displayLang } from '@/lib/lang'

export default async function SiteLayout({ children }: Readonly<{ children: ReactNode }>) {
  const lang = await displayLang()
  const [mode, labels, sidebarItems, logo, languages, wallet, me, games] = await Promise.all([
    displayMode(),
    getHeaderLabels(lang),
    getSidebarItems(lang),
    getLogo(),
    getLanguages(),
    getWallet(),
    getMe(),
    getGames(),
  ])
  const items = sidebarItems ?? []
  const pages = pagesByPath(games ?? [], items)

  return (
    <ModeProvider initial={mode}>
      <SportsBackdrop />
      <div className="flex min-h-screen">
        <Sidebar logo={logo} items={items} pages={pages} labels={labels} />

        <div className="flex min-w-0 flex-1 flex-col">
          <Header
            logo={logo}
            items={items}
            pages={pages}
            labels={labels}
            wallet={wallet}
            me={me}
            languages={languages}
            lang={lang}
          />
          <main className="flex-1 px-4 pb-6 sm:px-6 lg:px-10">{children}</main>
          <footer className="px-4 pb-5 text-xs text-muted sm:px-6 lg:px-10">{labels.demo_note}</footer>
        </div>
      </div>
    </ModeProvider>
  )
}
