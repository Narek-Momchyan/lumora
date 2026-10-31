import Image from 'next/image'
import { useId } from 'react'
import { multiplierColor } from '@/lib/zeus'
import type { SymbolDetails } from '@/types/zeus'

interface SlotSymbolProps {
  code: string
  symbols: SymbolDetails
}

function MultiplierSymbol({ value, color }: { value: string; color: string }) {
  const id = useId()

  return (
    <svg viewBox="0 0 100 100" className="h-full w-full" role="img" aria-label={value}>
      <defs>
        <radialGradient id={`${id}-fill`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--color-zeus-white)" stopOpacity="0.95" />
          <stop offset="100%" stopColor={color} />
        </radialGradient>
        <filter id={`${id}-glow`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <circle cx="50" cy="50" r="44" fill={color} opacity="0.1" />
      <circle cx="50" cy="50" r="40" fill="none" stroke={color} strokeWidth="3" opacity="0.9" />
      <circle cx="50" cy="50" r="37" fill={`url(#${id}-fill)`} opacity="0.08" />

      <text
        x="50"
        y="59"
        textAnchor="middle"
        fontSize={value.length > 2 ? '25' : '30'}
        fontWeight="900"
        fill={color}
        filter={`url(#${id}-glow)`}
      >
        {value}
      </text>

      <g opacity="0.6">
        <circle cx="50" cy="8" r="2.5" fill={color}>
          <animateTransform
            attributeName="transform"
            type="rotate"
            from="0 50 50"
            to="360 50 50"
            dur="3s"
            repeatCount="indefinite"
          />
        </circle>
      </g>
    </svg>
  )
}

// Multipliers have no picture: their name, like x25, is what the player reads.
export default function SlotSymbol({ code, symbols }: SlotSymbolProps) {
  const symbol = symbols[code]
  const color = multiplierColor(code)

  if (color) {
    return (
      <span className="block h-full w-full p-[6%]">
        <MultiplierSymbol value={symbol?.name ?? ''} color={color} />
      </span>
    )
  }

  if (!symbol?.image) return null

  return (
    <span className="relative block h-full w-full">
      {/* The pictures have empty margins: 120% fills the cell like in the original game. */}
      <span className="absolute -inset-[10%]">
        <Image
          src={symbol.image}
          alt={symbol.name}
          fill
          unoptimized
          sizes="120px"
          className={`zeus-symbol object-contain ${code === 'scatter' ? 'zeus-symbol-scatter' : ''}`}
        />
      </span>
    </span>
  )
}
