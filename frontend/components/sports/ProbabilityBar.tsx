interface ProbabilityBarProps {
  home: number // fair probabilities, 0..1
  draw: number
  away: number
}

// "Lumora model": the model's fair 1X2 probabilities as one bar (designs 06, 07).
export default function ProbabilityBar({ home, draw, away }: ProbabilityBarProps) {
  return (
    <div className="flex h-1.5 gap-px overflow-hidden rounded-full" aria-hidden="true">
      <span className="bg-accent" style={{ width: `${home * 100}%` }} />
      <span className="bg-muted" style={{ width: `${draw * 100}%` }} />
      <span className="bg-accent2" style={{ width: `${away * 100}%` }} />
    </div>
  )
}

export function percent(probability: number) {
  return `${Math.round(probability * 100)}%`
}
