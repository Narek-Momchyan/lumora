'use client'

import { useReducedMotion } from 'motion/react'
import { useRouter } from 'next/navigation'
import { useRef, useState } from 'react'
import { MODE_HOME } from '@/lib/mode'
import type { Mode } from '@/lib/mode'
import type { HeaderLabels } from '@/types/header'
import { applyTheme, useMode } from './ModeProvider'
import ModeWave from './ModeWave'

interface Wave {
  id: number
  mode: Mode
  x: number
  y: number
}

// Sports | Casino at the top of the sidebar (design 06). It opens the other section's home page.
export default function ModeSwitch({ labels, onSwitch }: { labels: HeaderLabels; onSwitch?: () => void }) {
  const router = useRouter()
  const mode = useMode()
  const reduceMotion = useReducedMotion()
  const [wave, setWave] = useState<Wave | null>(null)
  const nextId = useRef(0)

  function choose(target: Mode, button: HTMLButtonElement) {
    if (target === mode) return
    // The mobile drawer closes after the wave, which would end with it otherwise.
    if (onSwitch) window.setTimeout(onSwitch, reduceMotion ? 0 : 650)

    if (!reduceMotion) {
      const { left, top, width, height } = button.getBoundingClientRect()
      nextId.current += 1
      setWave({ id: nextId.current, mode: target, x: left + width / 2, y: top + height / 2 })
    }
    // The colours start their cross-fade now, under the wave, before the new page arrives.
    applyTheme(target)
    router.push(MODE_HOME[target])
  }

  const options: { mode: Mode; label: string }[] = [
    { mode: 'sports', label: labels.sports_mode },
    { mode: 'casino', label: labels.casino_mode },
  ]

  return (
    <>
      <div role="group" aria-label={labels.mode_switch_label} className="grid grid-cols-2 gap-1 rounded-xl border border-border bg-bg/40 p-1">
        {options.map((option) => {
          const active = option.mode === mode
          return (
            <button
              key={option.mode}
              type="button"
              aria-pressed={active}
              onClick={(event) => choose(option.mode, event.currentTarget)}
              className={`min-w-0 truncate rounded-lg px-2 py-2 text-sm font-semibold whitespace-nowrap transition-colors ${
                active
                  ? 'bg-linear-to-r from-accent to-accent2 text-bg shadow-md shadow-accent/20'
                  : 'text-muted hover:text-text'
              }`}
            >
              {option.label}
            </button>
          )
        })}
      </div>

      {wave && <ModeWave key={wave.id} mode={wave.mode} x={wave.x} y={wave.y} onDone={() => setWave(null)} />}
    </>
  )
}
