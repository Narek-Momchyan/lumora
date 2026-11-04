import type { Metadata } from 'next'
import { connection } from 'next/server'
import AuthCard from '@/components/auth/AuthCard'
import LoginHero from '@/components/auth/LoginHero'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import { getGames, getLanguages, getLoginPageLabels, getLogo } from '@/lib/content'
import { displayLang } from '@/lib/lang'

export async function generateMetadata(): Promise<Metadata> {
  await connection()
  const labels = await getLoginPageLabels(await displayLang())
  return { title: labels.page_title, description: labels.page_description }
}

export default async function LoginPage() {
  // The content is read per request, so the build doesn't need a running backend.
  await connection()
  const lang = await displayLang()
  const [labels, logo, languages, games] = await Promise.all([
    getLoginPageLabels(lang),
    getLogo(),
    getLanguages(),
    getGames(),
  ])

  return (
    <main className="relative grid min-h-screen bg-linear-to-br from-accent2/10 via-bg to-bg lg:grid-cols-[3fr_2fr]">
      <LoginHero logo={logo} games={games} labels={labels} />

      <section className="flex items-center justify-center px-6 pb-8 lg:bg-bg/60 lg:p-8">
        <AuthCard labels={labels} />
      </section>

      {languages && (
        <div className="absolute top-6 right-6 lg:top-8 lg:right-8">
          <LanguageSwitcher languages={languages} lang={lang} label={labels.language_switcher_label} />
        </div>
      )}

      <p className="px-6 pb-8 text-xs text-muted lg:absolute lg:bottom-12 lg:left-16 lg:p-0">{labels.footer_note}</p>
    </main>
  )
}
