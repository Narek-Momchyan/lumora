import type { Metadata } from 'next'
import { Inter, Noto_Sans_Armenian, Sora } from 'next/font/google'
import { connection } from 'next/server'
import type { ReactNode } from 'react'
import { getLogo } from '@/lib/content'
import { displayLang, htmlLang } from '@/lib/lang'
import './globals.css'

// globals.css picks the font by <html lang>: Sora and Inter don't have every language's letters.
const inter = Inter({ subsets: ['latin', 'cyrillic'], variable: '--font-inter' })
const sora = Sora({ subsets: ['latin'], variable: '--font-sora' })
const notoArmenian = Noto_Sans_Armenian({
  subsets: ['armenian', 'latin'],
  variable: '--font-noto-armenian',
  preload: false,
})

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const logo = await getLogo()
  return logo ? { title: logo.name } : {}
}

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const lang = await displayLang()

  return (
    <html lang={htmlLang(lang)} className={`${inter.variable} ${sora.variable} ${notoArmenian.variable}`}>
      <body className="bg-bg text-text antialiased">{children}</body>
    </html>
  )
}
