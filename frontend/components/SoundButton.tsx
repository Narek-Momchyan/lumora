'use client'

import type { SoundLabels } from '@/types/sound'

interface SoundButtonProps {
  muted: boolean
  volume: number
  onToggle: () => void
  onVolume: (volume: number) => void
  labels: SoundLabels
}

// The sound button of a game page: a speaker that is crossed out while the sound is off (the default), and a
// volume slider while it is on. Both texts come from the page's labels, in the player's language. Colours only
// through the tokens.
export default function SoundButton({ muted, volume, onToggle, onVolume, labels }: SoundButtonProps) {
  const label = muted ? labels.sound_on : labels.sound_off

  return (
    <div className="flex items-center justify-end gap-2">
      {!muted && (
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={volume}
          onChange={(event) => onVolume(Number(event.target.value))}
          aria-label={labels.sound_volume}
          title={labels.sound_volume}
          className="h-1.5 w-24 cursor-pointer accent-lime"
        />
      )}
      <button
        type="button"
        onClick={onToggle}
        aria-label={label}
        title={label}
        aria-pressed={!muted}
        className={`flex size-9 items-center justify-center rounded-lg border bg-surface2 transition-colors hover:border-muted ${
          muted ? 'border-border text-muted' : 'border-lime/50 text-lime'
        }`}
      >
        <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M11 5 6 9H3v6h3l5 4V5Z" />
          {muted ? (
            <>
              <path d="m16 9 5 6" />
              <path d="m21 9-5 6" />
            </>
          ) : (
            <>
              <path d="M15.5 8.5a5 5 0 0 1 0 7" />
              <path d="M18.5 5.5a9 9 0 0 1 0 13" />
            </>
          )}
        </svg>
      </button>
    </div>
  )
}
