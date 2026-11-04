'use client'

import { useState } from 'react'
import Card from '@/components/ui/Card'
import Tabs from '@/components/ui/Tabs'
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
    <Card as="div" large padding="none" className="w-full max-w-md p-6 sm:p-8">
      <Tabs tabs={tabs} value={tab} onChange={setTab} />

      <div className="mt-6">
        {tab === 'login' ? (
          <LoginForm labels={labels} onCreateAccount={() => setTab('signup')} />
        ) : (
          <SignupForm labels={labels} onLogin={() => setTab('login')} />
        )}
      </div>
    </Card>
  )
}
