'use client'

import { motion, useSpring, useTransform } from 'motion/react'
import { useEffect } from 'react'
import { formatCount } from '@/lib/zeus'

interface AnimatedNumberProps {
  value: number
  from?: number
  precision?: number
}

export default function AnimatedNumber({ value, from = value, precision = 2 }: AnimatedNumberProps) {
  const spring = useSpring(from, { mass: 0.8, stiffness: 75, damping: 15 })
  const display = useTransform(spring, (current) => formatCount(current, precision))

  useEffect(() => {
    spring.set(value)
  }, [value, spring])

  return <motion.span>{display}</motion.span>
}
