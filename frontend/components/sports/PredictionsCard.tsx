import Link from 'next/link'
import Card from '@/components/ui/Card'
import { buttonClass } from '@/components/ui/Button'
import { fill } from '@/lib/sports'
import type { PredictionLabels } from '@/types/predictions'

interface PredictionsCardProps {
  open: number // matches still open for predictions
  league: string // the league code the button opens
  labels: PredictionLabels
}

// The football home's side card (design 06): free score predictions, and where to make them.
export default function PredictionsCard({ open, league, labels }: PredictionsCardProps) {
  return (
    <Card padding="md" className="space-y-3">
      <h2 className="font-heading text-lg font-bold">{labels.predict_title}</h2>
      <p className="text-sm text-muted">{labels.predict_hint}</p>
      {open > 0 && <p className="text-xs text-muted">{fill(labels.open_left, { count: open })}</p>}
      <Link href={`/predictions?league=${league}`} className={buttonClass({ variant: 'outline', block: true })}>
        <span className="truncate">{labels.make_predictions}</span>
      </Link>
    </Card>
  )
}
