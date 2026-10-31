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
        className="w-full max-w-sm rounded-2xl border border-magenta bg-surface p-6"
      >
        <h2 id="buy-bonus-title" className="font-heading text-xl font-bold">
          {labels.buy_bonus_title}
        </h2>
        <p className="mt-2 text-sm text-muted">{labels.buy_bonus_text.replace('{amount}', price)}</p>

        <div className="mt-6 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl border border-border bg-surface2 px-4 py-3 text-sm font-medium text-text hover:border-muted"
          >
            {labels.cancel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-xl bg-linear-to-r from-cyan to-magenta px-4 py-3 text-sm font-semibold text-bg"
          >
            {labels.buy_bonus_confirm}
          </button>
        </div>
      </div>
    </div>
  )
}
