'use client'

import { useState } from 'react'
import { AUTO_SPIN_CHOICES } from '@/lib/zeus'
import type { ZeusPageLabels } from '@/types/zeus'

interface AutoplayMenuProps {
  autoLeft: number
  disabled: boolean
  labels: ZeusPageLabels
  onStart: (spins: number) => void
  onStop: () => void
}

const BUTTON = 'w-full rounded-xl border px-3 py-3 text-sm font-semibold transition-colors disabled:opacity-50'

export default function AutoplayMenu({ autoLeft, disabled, labels, onStart, onStop }: AutoplayMenuProps) {
  const [open, setOpen] = useState(false)

  if (autoLeft > 0) {
    return (
      <button type="button" onClick={onStop} className={`${BUTTON} border-danger text-danger`}>
        {labels.stop} · {labels.auto_spins_left.replace('{count}', String(autoLeft))}
      </button>
    )
  }

  return (
    <div className="relative">
      <button
        type="button"
        disabled={disabled}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className={`${BUTTON} border-border bg-surface2 text-text hover:border-muted`}
      >
        {labels.auto}
      </button>

      {open && (
        <div
          role="menu"
          aria-label={labels.auto_menu_label}
          className="absolute right-0 bottom-14 z-20 w-44 rounded-xl border border-border bg-surface p-2 shadow-lg shadow-bg"
        >
          <p className="mb-2 text-xs text-muted">{labels.auto_menu_label}</p>
          <div className="grid grid-cols-2 gap-1">
            {AUTO_SPIN_CHOICES.map((spins) => (
              <button
                key={spins}
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false)
                  onStart(spins)
                }}
                className="rounded-lg bg-surface2 px-2 py-2 text-sm font-semibold text-text hover:text-accent"
              >
                {spins}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
