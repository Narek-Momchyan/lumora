'use client'

import { useRouter } from 'next/navigation'
import type { Language } from '@/types/header'

const ONE_YEAR = 60 * 60 * 24 * 365

function saveLang(code: string) {
  document.cookie = `lang=${code}; path=/; max-age=${ONE_YEAR}; SameSite=Lax`
}

interface LanguageSwitcherProps {
  languages: Language[]
  lang: string
  label: string
}

export default function LanguageSwitcher({ languages, lang, label }: LanguageSwitcherProps) {
  const router = useRouter()

  function choose(code: string) {
    saveLang(code)
    router.refresh()
  }

  return (
    <nav aria-label={label} className="flex gap-1 rounded-xl border border-border bg-surface p-1">
      {languages.map(({ id, code, name }) => (
        <button
          key={id}
          type="button"
          aria-current={code === lang}
          onClick={() => choose(code)}
          className={`rounded-lg px-2 py-1.5 text-xs font-medium transition-colors sm:px-3 ${
            code === lang ? 'bg-surface2 text-text' : 'text-muted hover:text-text'
          }`}
        >
          {name}
        </button>
      ))}
    </nav>
  )
}
