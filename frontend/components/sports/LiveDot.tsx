// The pulsing red dot of a match in play. The pulse stops for visitors who ask for less motion.
export default function LiveDot() {
  return (
    <span className="relative flex size-2 shrink-0" aria-hidden="true">
      <span className="absolute inline-flex size-full rounded-full bg-danger opacity-75 motion-safe:animate-ping" />
      <span className="relative inline-flex size-2 rounded-full bg-danger" />
    </span>
  )
}
