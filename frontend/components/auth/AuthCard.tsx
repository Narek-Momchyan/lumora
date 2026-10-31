'use client'

import { useState } from 'react'
import type { LoginPageLabels } from '@/types/account'
import LoginForm from './LoginForm'
import SignupForm from './SignupForm'

type Tab = 'login' | 'signup'

export default function AuthCard({ labels }: { labels: LoginPageLabels }) {
  const [tab, setTab] = useState<Tab>('login')

  const tabs: { id: Tab; label: string }[] = [
    { id: 'login', label: labels.tab_login },
    { id: 'signup', label: labels.tab_signup },
  ]

  return (
    <div className="w-full max-w-md rounded-3xl border border-border bg-surface p-6 sm:p-8">
      <div role="tablist" className="grid grid-cols-2 gap-1 rounded-xl bg-surface2 p-1">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`rounded-lg py-2 text-sm font-medium transition-colors ${
              tab === id ? 'bg-surface text-text' : 'text-muted hover:text-text'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === 'login' ? (
          <LoginForm labels={labels} onCreateAccount={() => setTab('signup')} />
        ) : (
          <SignupForm labels={labels} onLogin={() => setTab('login')} />
        )}
      </div>
    </div>
  )
}
