import type { SportsUiLabels } from '@/types/sports'

const TONES: Record<string, string> = { W: 'bg-lime text-bg', D: 'bg-muted/40 text-text', L: 'bg-danger text-text' }

// The last results of a club, newest first: W D L, drawn as small coloured squares.
export default function FormDots({
  form,
  labels,
}: {
  form: string[]
  labels: Pick<SportsUiLabels, 'form_win' | 'form_draw' | 'form_loss'>
}) {
  const letters: Record<string, string> = { W: labels.form_win, D: labels.form_draw, L: labels.form_loss }
  return (
    <span className="inline-flex gap-1" aria-hidden="true">
      {form.map((result, index) => (
        <span
          key={index}
          className={`flex size-5 items-center justify-center rounded text-[10px] font-bold ${TONES[result]}`}
        >
          {letters[result]}
        </span>
      ))}
    </span>
  )
}
