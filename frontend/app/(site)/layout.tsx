import type { ReactNode } from 'react'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import { getHeaderLabels, getLanguages, getLogo, getMe, getSidebarItems, getWallet } from '@/lib/content'
import { displayLang } from '@/lib/lang'

export default async function SiteLayout({ children }: Readonly<{ children: ReactNode }>) {
  const lang = await displayLang()
  const [labels, items, logo, languages, wallet, me] = await Promise.all([
    getHeaderLabels(lang),
    getSidebarItems(lang),
    getLogo(),
    getLanguages(),
    getWallet(),
    getMe(),
  ])

  return (
    <div className="flex min-h-screen">
      <Sidebar logo={logo} items={items ?? []} labels={labels} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header logo={logo} labels={labels} wallet={wallet} me={me} languages={languages} lang={lang} />
        <main className="flex-1 px-4 pb-8 sm:px-6 lg:px-10">{children}</main>
        <footer className="px-4 pb-6 text-xs text-muted sm:px-6 lg:px-10">{labels.demo_note}</footer>
      </div>
    </div>
  )
}
