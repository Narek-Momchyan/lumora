'use client'

import { motion } from 'motion/react'
import Image from 'next/image'

export default function GameHero({ image, attacking }: { image: string | null; attacking: boolean }) {
  if (!image) return null

  return (
    <motion.div
      className="relative hidden aspect-square w-full overflow-hidden rounded-2xl border border-border lg:block"
      animate={attacking ? { scale: [1, 1.05, 1], filter: 'brightness(1.3)' } : { scale: 1, filter: 'brightness(1)' }}
      transition={{ duration: 0.35 }}
    >
      <Image src={image} alt="" fill unoptimized loading="eager" sizes="240px" className="object-cover" />
    </motion.div>
  )
}
