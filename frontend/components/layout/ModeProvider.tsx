'use client'

import { usePathname } from 'next/navigation'
import { createContext, use, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { modeForPath } from '@/lib/mode'
import type { Mode } from '@/lib/mode'

const ModeContext = createContext<Mode>('sports')

// globals.css switches the colours on <html data-theme>, with a cross-fade.
export function applyTheme(mode: Mode) {
  document.documentElement.dataset.theme = mode
}

// The current section for the sidebar and the switch. The layout doesn't re-render when the player
// moves between pages, so the section follows the route here, and shared pages keep the last one.
export default function ModeProvider({ initial, children }: { initial: Mode; children: ReactNode }) {
  const pathname = usePathname()
  const pathMode = modeForPath(pathname)
  const [lastMode, setLastMode] = useState(initial)

  if (pathMode && pathMode !== lastMode) setLastMode(pathMode)
  const mode = pathMode ?? lastMode

  // The colours follow the section too.
  useEffect(() => applyTheme(mode), [mode])

  return <ModeContext value={mode}>{children}</ModeContext>
}

export function useMode() {
  return use(ModeContext)
}
