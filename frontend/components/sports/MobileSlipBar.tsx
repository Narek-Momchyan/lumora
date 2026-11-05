'use client'

import { useSlip, useSlipContext } from './SlipProvider'

// Below lg the bet slip sits at the end of the page: this bar, fixed at the bottom, shows how many
// picks it holds and takes the player to it.
export default function MobileSlipBar() {
  const context = useSlipContext()
  const count = useSlip().picks.length
  if (!context || count === 0) return null

  return (
    <a
      href="#bet-slip"
      className="fixed inset-x-4 bottom-4 z-30 flex h-12 items-center justify-between rounded-xl bg-linear-to-r from-accent to-accent2 px-4 text-sm font-semibold text-bg shadow-lg shadow-bg lg:hidden"
    >
      <span>{context.ui.slip_title}</span>
      <span className="flex size-6 items-center justify-center rounded-full bg-bg text-xs text-lime">{count}</span>
    </a>
  )
}
