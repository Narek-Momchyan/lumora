import Card from '@/components/ui/Card'
import type { ForumLabels } from '@/types/forums'

// The forum rules (design 11): two things to do, two not to, and how reports and bans work. All text comes
// from the admin, so it can change without a release.
export default function ForumRules({ labels }: { labels: ForumLabels }) {
  const rules = [
    { text: labels.rule_respect, good: true },
    { text: labels.rule_on_topic, good: true },
    { text: labels.rule_no_betting, good: false },
    { text: labels.rule_no_personal, good: false },
  ]

  return (
    <Card padding="md" className="space-y-4">
      <h2 className="font-heading text-lg font-bold">{labels.rules_title}</h2>
      <ul className="space-y-2 text-sm">
        {rules.map(({ text, good }) => (
          <li key={text} className="flex items-start gap-2">
            <span aria-hidden="true" className={`mt-0.5 font-bold ${good ? 'text-lime' : 'text-danger'}`}>
              {good ? '✓' : '✕'}
            </span>
            <span>{text}</span>
          </li>
        ))}
      </ul>
      <p className="text-center text-xs text-muted">{labels.rules_note}</p>
    </Card>
  )
}
