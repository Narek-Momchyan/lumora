'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import type { HeaderLabels, Language } from '@/types/header'

interface AvatarMenuProps {
  name?: string
  languages: Language[] | null
  lang: string
  labels: HeaderLabels
}

export default function AvatarMenu({ name, languages, lang, labels }: AvatarMenuProps) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  async function logout() {
    setPending(true)
    setError('')

    try {
      await apiFetch('/logout', { method: 'POST' })
      router.replace('/login')
      router.refresh()
    } catch (exception) {
      setPending(false)
      if (!(exception instanceof ApiError)) throw exception
      setError(errorDetail(exception, labels.server_unreachable))
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={labels.menu_label}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="block size-10 rounded-full bg-linear-to-br from-accent2 to-bg"
      />

      {open && (
        <>
          <button
            type="button"
            aria-hidden="true"
            tabIndex={-1}
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-10 cursor-default"
          />

          <div className="absolute top-12 right-0 z-20 w-64 space-y-4 rounded-2xl border border-border bg-surface p-4 shadow-lg shadow-bg">
            <p className="truncate font-semibold">{name}</p>

            {languages && (
              <div>
                <p className="mb-2 text-xs text-muted">{labels.language_label}</p>
                <LanguageSwitcher languages={languages} lang={lang} label={labels.language_label} />
              </div>
            )}

            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}

            <button
              type="button"
              disabled={pending}
              onClick={logout}
              className="w-full rounded-xl border border-border bg-surface2 px-4 py-2 text-sm font-medium text-text transition-colors hover:border-muted disabled:opacity-60"
            >
              {labels.logout_button}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
