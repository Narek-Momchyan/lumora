'use client'

import { useEffect, useState } from 'react'
import Logo from '@/components/Logo'
import type { HeaderLabels, Logo as LogoData, PageInfo, SidebarItem } from '@/types/header'
import SidebarNav from './SidebarNav'

interface MobileNavProps {
  logo: LogoData | null
  items: SidebarItem[]
  pages: Record<string, PageInfo>
  labels: HeaderLabels
}

const LINE = 'block h-0.5 w-5 rounded-full bg-text transition-transform'

// Below lg: the burger opens the sidebar as a drawer from the left.
export default function MobileNav({ logo, items, pages, labels }: MobileNavProps) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    // The page under the drawer doesn't scroll while it is open.
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  return (
    <div className="lg:hidden">
      <button
        type="button"
        aria-label={labels.open_menu_label}
        aria-expanded={open}
        onClick={() => setOpen(true)}
        className="flex size-10 flex-col items-center justify-center gap-1.5 rounded-xl border border-border bg-surface"
      >
        <span className={LINE} />
        <span className={LINE} />
        <span className={LINE} />
      </button>

      {open && (
        <div className="fixed inset-0 z-40">
          <button
            type="button"
            aria-label={labels.close_menu_label}
            onClick={() => setOpen(false)}
            className="absolute inset-0 cursor-default bg-bg/70 backdrop-blur-sm"
          />

          <div
            role="dialog"
            aria-modal="true"
            aria-label={labels.navigation_label}
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col overflow-y-auto border-r border-border bg-surface px-4 py-6"
          >
            <div className="flex items-center justify-between gap-3">
              <Logo logo={logo} />
              <button
                type="button"
                aria-label={labels.close_menu_label}
                onClick={() => setOpen(false)}
                className="relative size-10 shrink-0 rounded-xl border border-border bg-surface2"
              >
                <span className={`${LINE} absolute top-1/2 left-1/2 -translate-1/2 rotate-45`} />
                <span className={`${LINE} absolute top-1/2 left-1/2 -translate-1/2 -rotate-45`} />
              </button>
            </div>

            <div className="mt-8">
              <SidebarNav items={items} pages={pages} labels={labels} onNavigate={() => setOpen(false)} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
