import Image from 'next/image'
import type { Logo as LogoData } from '@/types/header'

export default function Logo({ logo }: { logo: LogoData | null }) {
  if (!logo) return null

  return (
    <div className="flex items-center gap-2">
      <Image src={logo.image} alt="" width={24} height={24} unoptimized />
      <span className="font-heading text-lg font-bold text-text">{logo.name}</span>
    </div>
  )
}
