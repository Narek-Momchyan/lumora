import Image from 'next/image'
import type { SymbolDetails } from '@/types/zeus'

interface SlotSymbolProps {
  code: string
  symbols: SymbolDetails
}

// Multipliers have no picture: their name, like x25, is what the player reads.
export default function SlotSymbol({ code, symbols }: SlotSymbolProps) {
  const symbol = symbols[code]

  if (!symbol?.image) {
    return (
      <span className="flex h-full items-center justify-center font-heading text-sm font-bold text-lime sm:text-xl">
        {symbol?.name}
      </span>
    )
  }

  return (
    <span className="relative block h-full w-full">
      <Image src={symbol.image} alt={symbol.name} fill unoptimized sizes="96px" className="object-contain" />
    </span>
  )
}
