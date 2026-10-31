import type { Metadata } from 'next'
import { connection } from 'next/server'
import AuthCard from '@/components/auth/AuthCard'
import LoginHero from '@/components/auth/LoginHero'
import { apiFetch } from '@/lib/api'
import type { Game } from '@/types/game'

export const metadata: Metadata = {
  title: 'Log in · Lumora',
}

async function loadGames() {
  try {
    return await apiFetch<Game[]>('/games', { auth: false, cache: 'no-store' })
  } catch {
    return null
  }
}

export default async function LoginPage() {
  // The stats are read per request, so the build doesn't need a running backend.
  await connection()
  const games = await loadGames()

  return (
    <main className="relative grid min-h-screen bg-linear-to-br from-magenta/10 via-bg to-bg lg:grid-cols-[3fr_2fr]">
      <LoginHero games={games} />

      <section className="flex items-center justify-center px-6 pb-8 lg:bg-bg/60 lg:p-8">
        <AuthCard />
      </section>

      <p className="px-6 pb-8 text-xs text-muted lg:absolute lg:bottom-12 lg:left-16 lg:p-0">
        18+ · Demo play only · Lumora coins have no cash value
      </p>
    </main>
  )
}
