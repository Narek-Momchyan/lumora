// A turning ring in the accent colour. It has no text on purpose: nothing is hard-coded, and the words of the
// page come from the admin only once the page has loaded. The turning stops for visitors who ask for less motion.
export default function Spinner({ size = 'md' }: { size?: 'md' | 'lg' }) {
  return (
    <span
      aria-hidden="true"
      className={`block rounded-full border-accent/20 border-t-accent motion-safe:animate-spin ${
        size === 'lg' ? 'size-24 border-4' : 'size-10 border-[3px]'
      }`}
    />
  )
}
