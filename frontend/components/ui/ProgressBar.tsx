// A thin cyan-to-magenta bar, e.g. under the roulette countdown. `value` goes from 0 to 1.
export default function ProgressBar({ value }: { value: number }) {
  const percent = Math.min(100, Math.max(0, value * 100))

  return (
    <div className="h-1.5 overflow-hidden rounded-full bg-surface2" aria-hidden="true">
      <div
        className="h-full rounded-full bg-linear-to-r from-cyan to-magenta transition-[width] duration-1000 ease-linear"
        style={{ width: `${percent}%` }}
      />
    </div>
  )
}
