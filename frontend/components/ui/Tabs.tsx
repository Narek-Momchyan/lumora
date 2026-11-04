interface Tab<T extends string> {
  id: T
  label: string
}

interface TabsProps<T extends string> {
  tabs: Tab<T>[]
  value: T
  onChange: (id: T) => void
  label?: string // for screen readers
}

// A segmented control: Log in / Sign up, Single / Express, Manual / Auto (designs 01, 03, 06).
export default function Tabs<T extends string>({ tabs, value, onChange, label }: TabsProps<T>) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className="grid gap-1 rounded-xl bg-surface2 p-1"
      style={{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === value}
          onClick={() => onChange(tab.id)}
          className={`min-w-0 truncate rounded-lg py-2 text-sm font-medium transition-colors ${
            tab.id === value ? 'bg-bg text-text shadow-sm' : 'text-muted hover:text-text'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
