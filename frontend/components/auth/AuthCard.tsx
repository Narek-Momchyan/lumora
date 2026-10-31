'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, useSyncExternalStore } from 'react'
import { isLoggedIn } from '@/lib/api'
import LoginForm from './LoginForm'
import SignupForm from './SignupForm'

type Tab = 'login' | 'signup'

const TABS: { id: Tab; label: string }[] = [
  { id: 'login', label: 'Log in' },
  { id: 'signup', label: 'Sign up' },
]

const subscribe = () => () => {}

export default function AuthCard() {
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('login')
  const [loginEmail, setLoginEmail] = useState('')
  const [notice, setNotice] = useState('')

  // null on the server: tokens are in localStorage, so the card stays hidden until the
  // browser has checked them and a logged-in player never sees the form.
  const loggedIn = useSyncExternalStore(subscribe, isLoggedIn, () => null)

  useEffect(() => {
    if (loggedIn) router.replace('/')
  }, [loggedIn, router])

  function showLogin(email = '', message = '') {
    setLoginEmail(email)
    setNotice(message)
    setTab('login')
  }

  return (
    <div
      className={`w-full max-w-md rounded-3xl border border-border bg-surface p-6 sm:p-8 ${
        loggedIn === false ? '' : 'invisible'
      }`}
    >
      <div role="tablist" className="grid grid-cols-2 gap-1 rounded-xl bg-surface2 p-1">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => (id === 'login' ? showLogin() : setTab('signup'))}
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
          <LoginForm
            defaultEmail={loginEmail}
            notice={notice}
            onCreateAccount={() => setTab('signup')}
          />
        ) : (
          <SignupForm
            onLogin={() => showLogin()}
            onLoginFailed={(email) =>
              showLogin(email, 'Your account is ready. Please log in.')
            }
          />
        )}
      </div>
    </div>
  )
}
