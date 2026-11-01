'use client'

import { useRef } from 'react'
import type { RefObject } from 'react'
import { WHEEL, colorOf } from '@/lib/roulette'
import useServerFrame from '@/lib/useServerFrame'
import type { RouletteRound } from '@/types/roulette'

const STEP = 360 / WHEEL.length
const SIZE = 400
const CENTER = SIZE / 2
const OUTER = 192
const INNER = 148
const LABEL = 172
const BALL_OUT = 186
const BALL_IN = 158
const WHEEL_TURNS = 5
const BALL_TURNS = 9

const FILLS = { red: 'fill-danger', black: 'fill-bg', green: 'fill-lime' }

function point(radius: number, degrees: number) {
  const radians = ((degrees - 90) * Math.PI) / 180
  return `${CENTER + radius * Math.cos(radians)} ${CENTER + radius * Math.sin(radians)}`
}

function sector(index: number) {
  const from = index * STEP - STEP / 2
  const to = from + STEP
  return `M ${point(OUTER, from)} A ${OUTER} ${OUTER} 0 0 1 ${point(OUTER, to)} L ${point(INNER, to)} A ${INNER} ${INNER} 0 0 0 ${point(INNER, from)} Z`
}

// The turn that puts a pocket under the pointer at the top.
function restAngle(pocket: number) {
  return -WHEEL.indexOf(pocket) * STEP
}

function nearestTurn(degrees: number) {
  return ((degrees % 360) + 540) % 360 - 180
}

interface WheelProps {
  round: RouletteRound | null
  previous: number | undefined
  clockOffset: RefObject<number | null>
}

export default function Wheel({ round, previous, clockOffset }: WheelProps) {
  const wheelRef = useRef<SVGGElement>(null)
  const ballRef = useRef<SVGGElement>(null)
  const ballDotRef = useRef<SVGCircleElement>(null)

  useServerFrame(clockOffset, (serverNow) => {
    if (!wheelRef.current || !ballRef.current || !ballDotRef.current) return

    const from = restAngle(previous ?? 0)
    let wheel = from
    let ball = 0
    let radius = BALL_IN

    if (round?.result !== undefined && round.spin_started_at && round.spin_ends_at) {
      const start = Date.parse(round.spin_started_at)
      const left = Math.max(0, 1 - (serverNow - start) / (Date.parse(round.spin_ends_at) - start))
      const slowing = left ** 3 // the wheel slows down until it stops exactly on the result
      const target = restAngle(round.result)
      // The position comes from the time, so a page opened in the middle of a spin is right too.
      wheel = target + (nearestTurn(from - target) + WHEEL_TURNS * 360) * slowing
      ball = -BALL_TURNS * 360 * slowing
      radius = BALL_IN + (BALL_OUT - BALL_IN) * Math.min(1, left * 4)
    }

    wheelRef.current.setAttribute('transform', `rotate(${wheel} ${CENTER} ${CENTER})`)
    ballRef.current.setAttribute('transform', `rotate(${ball} ${CENTER} ${CENTER})`)
    ballDotRef.current.setAttribute('cy', String(CENTER - radius))
  })

  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} aria-hidden="true" className="aspect-square h-full max-h-full max-w-full">
      <circle cx={CENTER} cy={CENTER} r={OUTER + 6} className="fill-surface stroke-border" strokeWidth="2" />
      <g ref={wheelRef}>
        {WHEEL.map((pocket, index) => (
          <path key={pocket} d={sector(index)} className={`${FILLS[colorOf(pocket)]} stroke-border`} strokeWidth="1" />
        ))}
        {WHEEL.map((pocket, index) => (
          <text
            key={pocket}
            x={CENTER}
            y={CENTER - LABEL}
            transform={`rotate(${index * STEP} ${CENTER} ${CENTER})`}
            textAnchor="middle"
            dominantBaseline="central"
            className={`font-sans text-[13px] font-bold ${colorOf(pocket) === 'green' ? 'fill-bg' : 'fill-text'}`}
          >
            {pocket}
          </text>
        ))}
        <circle cx={CENTER} cy={CENTER} r={INNER} className="fill-surface2 stroke-border" strokeWidth="2" />
        {[0, 60, 120, 180, 240, 300].map((angle) => (
          <line
            key={angle}
            x1={CENTER}
            y1={CENTER - 44}
            x2={CENTER}
            y2={CENTER - 130}
            transform={`rotate(${angle} ${CENTER} ${CENTER})`}
            className="stroke-border"
            strokeWidth="2"
          />
        ))}
      </g>
      <circle cx={CENTER} cy={CENTER} r="40" className="fill-cyan" />
      <circle cx={CENTER} cy={CENTER} r="26" className="fill-magenta" />
      <circle cx={CENTER} cy={CENTER} r="11" className="fill-bg" />
      <g ref={ballRef}>
        <circle ref={ballDotRef} cx={CENTER} cy={CENTER - BALL_IN} r="7" className="fill-text" />
      </g>
      <path d={`M ${CENTER - 11} 0 L ${CENTER + 11} 0 L ${CENTER} 16 Z`} className="fill-cyan" />
    </svg>
  )
}
