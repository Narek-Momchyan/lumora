'use client'

import { useRef } from 'react'
import type { RefObject } from 'react'
import { curveAt, multiplierAt } from '@/lib/crash'
import type { CrashPageLabels, CrashRound } from '@/types/crash'
import useFlightFrame from './useFlightFrame'

const PADDING = 32
const GRID_LINES = 4
const CURVE_STEPS = 80
const MIN_WINDOW_MS = 12000
const MIN_TOP_MULTIPLIER = 2
const ROOM_AHEAD = 1.2

function themeColor(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim()
}

function fitToScreen(canvas: HTMLCanvasElement) {
  const scale = window.devicePixelRatio || 1
  const width = Math.round(canvas.clientWidth * scale)
  const height = Math.round(canvas.clientHeight * scale)
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width
    canvas.height = height
  }
  return scale
}

function drawGrid(context: CanvasRenderingContext2D, width: number, height: number) {
  context.strokeStyle = themeColor('border')
  context.lineWidth = 1
  context.shadowBlur = 0
  for (let line = 1; line <= GRID_LINES; line++) {
    const y = Math.round((height * line) / (GRID_LINES + 1)) + 0.5
    context.beginPath()
    context.moveTo(0, y)
    context.lineTo(width, y)
    context.stroke()
  }
}

function drawCurve(context: CanvasRenderingContext2D, width: number, height: number, flight: number, crashed: boolean) {
  const windowMs = Math.max(MIN_WINDOW_MS, flight * ROOM_AHEAD)
  const top = Math.max(MIN_TOP_MULTIPLIER, 1 + (curveAt(flight) - 1) * ROOM_AHEAD)
  const x = (ms: number) => PADDING + (ms / windowMs) * (width - PADDING * 2)
  const y = (ms: number) => height - PADDING - ((curveAt(ms) - 1) / (top - 1)) * (height - PADDING * 2)
  const color = themeColor(crashed ? 'danger' : 'cyan')

  context.strokeStyle = color
  context.shadowColor = color
  context.shadowBlur = 16
  context.lineWidth = 4
  context.lineCap = 'round'
  context.beginPath()
  context.moveTo(x(0), y(0))
  for (let step = 1; step <= CURVE_STEPS; step++) {
    const ms = (flight * step) / CURVE_STEPS
    context.lineTo(x(ms), y(ms))
  }
  context.stroke()

  context.fillStyle = themeColor(crashed ? 'danger' : 'magenta')
  context.shadowColor = context.fillStyle
  context.beginPath()
  context.arc(x(flight), y(flight), 8, 0, Math.PI * 2)
  context.fill()
}

interface CrashChartProps {
  round: CrashRound | null
  connected: boolean
  clockOffset: RefObject<number | null>
  labels: CrashPageLabels
}

export default function CrashChart({ round, connected, clockOffset, labels }: CrashChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const multiplierRef = useRef<HTMLParagraphElement>(null)
  const statusRef = useRef<HTMLParagraphElement>(null)

  function statusText(multiplier: string, serverNow: number) {
    if (!connected) return labels.connecting
    if (round?.status === 'crashed') return labels.crashed_status.replace('{multiplier}', multiplier)
    if (round?.status === 'flying') return labels.flying_status
    if (round?.status !== 'betting') return labels.waiting_status
    const left = Math.max(0, Math.ceil((Date.parse(round.betting_ends_at) - serverNow) / 1000))
    return labels.betting_status.replace('{seconds}', String(left))
  }

  useFlightFrame(round, clockOffset, (flight, serverNow) => {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (!canvas || !context || !multiplierRef.current || !statusRef.current) return

    const crashed = round?.status === 'crashed'
    const multiplier = crashed ? (round.crash_point ?? '') : multiplierAt(flight).toFixed(2)
    multiplierRef.current.textContent = `${multiplier}x`
    multiplierRef.current.classList.toggle('text-danger', crashed)
    statusRef.current.textContent = statusText(multiplier, serverNow)

    const scale = fitToScreen(canvas)
    const width = canvas.width / scale
    const height = canvas.height / scale
    context.setTransform(scale, 0, 0, scale, 0, 0)
    context.clearRect(0, 0, width, height)
    drawGrid(context, width, height)
    if (round?.status === 'flying' || crashed) drawCurve(context, width, height, flight, crashed)
  })

  return (
    <section className="relative min-h-40 flex-1 overflow-hidden rounded-2xl md:min-h-0 border border-border bg-linear-to-b from-surface2 to-bg">
      <canvas ref={canvasRef} aria-hidden="true" className="absolute inset-0 size-full" />
      <div className="relative p-4 sm:p-6">
        <p ref={multiplierRef} aria-live="off" className="font-heading text-4xl font-bold tabular-nums sm:text-6xl" />
        <p ref={statusRef} className="mt-1 text-xs text-muted sm:text-sm" />
      </div>
    </section>
  )
}
