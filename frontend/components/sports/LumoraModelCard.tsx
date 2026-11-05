import Card from '@/components/ui/Card'
import SectionTitle from '@/components/ui/SectionTitle'
import type { SportsUiLabels } from '@/types/sports'

// Says in plain words where the odds come from: the Lumora model, not a bookmaker's feed.
export default function LumoraModelCard({ labels }: { labels: SportsUiLabels }) {
  return (
    <Card padding="md" className="space-y-3">
      <SectionTitle title={labels.model_card_title} aside={labels.lumora_model} />
      <p className="text-sm text-muted">{labels.model_card_text}</p>
    </Card>
  )
}
