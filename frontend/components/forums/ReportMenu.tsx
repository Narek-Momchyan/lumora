'use client'

import { useState } from 'react'
import Button from '@/components/ui/Button'
import { ApiError, apiFetch, errorDetail } from '@/lib/api'
import { RULES, ruleLabel } from '@/lib/forums'
import type { ForumLabels, ForumRule } from '@/types/forums'

interface ReportMenuProps {
  post: number
  labels: ForumLabels
  serverUnreachable: string
}

// The Report button of a post (design 12): a small dialog with the four reasons and Send. The server allows
// one report per player and post, and says so in the player's language if it is sent twice.
export default function ReportMenu({ post, labels, serverUnreachable }: ReportMenuProps) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState<ForumRule>('spam_ads')
  const [pending, setPending] = useState(false)
  const [note, setNote] = useState('')
  const [failed, setFailed] = useState(false)

  async function send() {
    setPending(true)
    setNote('')
    try {
      await apiFetch('/post_reports', { method: 'POST', body: { post, reason } })
      setFailed(false)
      setNote(labels.report_sent)
      setOpen(false)
    } catch (caught) {
      setFailed(true)
      setNote(caught instanceof ApiError ? errorDetail(caught, serverUnreachable) : serverUnreachable)
      setOpen(false)
    } finally {
      setPending(false)
    }
  }

  return (
    <span className="relative inline-flex items-center gap-2">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="text-xs text-muted transition-colors hover:text-text"
      >
        ⚑ {labels.report}
      </button>
      {note && (
        <span role="status" className={`text-xs ${failed ? 'text-danger' : 'text-lime'}`}>
          {note}
        </span>
      )}
      {open && (
        <div className="absolute right-0 bottom-full z-10 mb-2 w-60 space-y-3 rounded-2xl border border-border bg-surface p-4 shadow-2xl">
          <p className="text-sm font-semibold">{labels.report_title}</p>
          <fieldset className="space-y-2">
            {RULES.map((item) => (
              <label key={item} className="flex cursor-pointer items-center gap-2 text-sm">
                <input type="radio" name={`report-${post}`} checked={reason === item} onChange={() => setReason(item)} className="size-4 accent-lime" />
                {ruleLabel(item, labels)}
              </label>
            ))}
          </fieldset>
          <Button variant="outline" block disabled={pending} onClick={send}>
            {labels.send_report}
          </Button>
        </div>
      )}
    </span>
  )
}
