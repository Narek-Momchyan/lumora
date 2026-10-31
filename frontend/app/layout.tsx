import type { Metadata } from 'next'
import { Inter, Sora } from 'next/font/google'
import type { ReactNode } from 'react'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const sora = Sora({ subsets: ['latin'], variable: '--font-sora' })

export const metadata: Metadata = {
  title: 'Lumora',
  description: 'Casino-style games with demo coins. Lumora Coins (LC) have no cash value.',
}

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${sora.variable}`}>
      <body className="bg-bg text-text antialiased">{children}</body>
    </html>
  )
}
