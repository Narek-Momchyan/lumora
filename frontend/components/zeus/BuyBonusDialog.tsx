import Button from '@/components/ui/Button'
import type { ZeusPageLabels } from '@/types/zeus'

interface BuyBonusDialogProps {
  price: string
  labels: ZeusPageLabels
  onConfirm: () => void
  onCancel: () => void
}

export default function BuyBonusDialog({ price, labels, onConfirm, onCancel }: BuyBonusDialogProps) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-bg/80 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="buy-bonus-title"
        className="w-full max-w-sm rounded-2xl border border-accent2 bg-surface p-6"
      >
        <h2 id="buy-bonus-title" className="font-heading text-xl font-bold">
          {labels.buy_bonus_title}
        </h2>
        <p className="mt-2 text-sm text-muted">{labels.buy_bonus_text.replace('{amount}', price)}</p>

        <div className="mt-6 grid grid-cols-2 gap-2">
          <Button variant="ghost" size="lg" onClick={onCancel}>
            {labels.cancel}
          </Button>
          <Button size="lg" onClick={onConfirm}>
            {labels.buy_bonus_confirm}
          </Button>
        </div>
      </div>
    </div>
  )
}
