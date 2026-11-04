import type { SportsPageLabels } from '@/types/sports'

const LINE = 'absolute border-text/15'

// The green hero of the football pages (design 06, 07): a dark pitch with its lines drawn in CSS.
export default function PitchHero({ labels }: { labels: SportsPageLabels }) {
  return (
    <section className="relative overflow-hidden rounded-3xl border border-border bg-linear-to-br from-accent2/25 via-surface to-bg px-6 py-12 sm:px-12 sm:py-16 lg:py-20">
      {/* The pitch: halfway line, centre circle and both penalty boxes. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <span className={`${LINE} inset-y-0 left-1/2 border-l`} />
        <span className={`${LINE} top-1/2 left-1/2 size-40 -translate-1/2 rounded-full border sm:size-56`} />
        <span className={`${LINE} top-1/2 left-1/2 size-2 -translate-1/2 rounded-full bg-text/20`} />
        <span className={`${LINE} inset-y-[22%] left-0 w-[12%] border-y border-r`} />
        <span className={`${LINE} inset-y-[22%] right-0 w-[12%] border-y border-l`} />
        <span className="absolute inset-x-0 top-0 h-1/2 bg-linear-to-b from-accent/10 to-transparent" />
      </div>

      <div className="relative max-w-2xl">
        <p className="text-xs font-semibold tracking-widest text-lime uppercase">{labels.hero_eyebrow}</p>
        <h2 className="mt-3 font-heading text-4xl leading-tight font-bold sm:text-5xl lg:text-6xl">{labels.hero_title}</h2>
        <p className="mt-4 max-w-xl text-sm text-text/80 sm:text-base">{labels.hero_text}</p>
      </div>
    </section>
  )
}
