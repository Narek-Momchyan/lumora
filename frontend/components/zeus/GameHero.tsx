'use client'

import { motion } from 'motion/react'
import Image from 'next/image'

export default function GameHero({ image, attacking }: { image: string | null; attacking: boolean }) {
  if (!image) return null

  return (
    <motion.div
      className="relative hidden aspect-square w-full overflow-hidden rounded-full border-4 border-zeus-gold shadow-[0_0_25px_var(--color-zeus-gold)] lg:block"
      animate={
        attacking
          ? { scale: [1, 1.06, 1], filter: ['brightness(1)', 'brightness(1.25)', 'brightness(1)'] }
          : { y: [0, -6, 0] }
      }
      transition={attacking ? { duration: 0.35 } : { duration: 4, repeat: Infinity, ease: 'easeInOut' }}
    >
      <Image src={image} alt="" fill unoptimized loading="eager" sizes="240px" className="object-cover" />
    </motion.div>
  )
}
