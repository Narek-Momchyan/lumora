'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, apiFetch, fieldErrors, login } from '@/lib/api'
import type { FieldErrors } from '@/lib/api'
import type { RegisteredPlayer, RegisterPayload } from '@/types/account'
import TextField from './TextField'

interface SignupFormProps {
  onLogin: () => void
  onLoginFailed: (email: string) => void
}

export default function SignupForm({ onLogin, onLoginFailed }: SignupFormProps) {
  const router = useRouter()
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const payload: RegisterPayload = {
      email: String(form.get('email')),
      password: String(form.get('password')),
      display_name: String(form.get('display_name')).trim(),
    }

    setPending(true)
    setErrors({})
    setFormError('')

    try {
      await apiFetch<RegisteredPlayer>('/register', { method: 'POST', body: payload, auth: false })
    } catch (error) {
      setPending(false)
      if (!(error instanceof ApiError)) throw error

      const fields = fieldErrors(error)
      setErrors(fields)
      if (!fields.email && !fields.password && !fields.display_name) setFormError(error.message)
      return
    }

    // The account exists now, so a failed login must not look like a failed sign up.
    try {
      await login(payload.email, payload.password)
      router.replace('/')
    } catch {
      onLoginFailed(payload.email)
    }
  }

  return (
    <>
      <h2 className="font-heading text-2xl font-bold">Create your account</h2>
      <p className="mt-1 text-sm text-muted">Start with 10,000 LC of demo coins.</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <TextField
          label="Email"
          name="email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          required
          errors={errors.email}
        />
        <TextField
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          errors={errors.password}
        />
        <TextField
          label="Display name (optional)"
          name="display_name"
          autoComplete="nickname"
          errors={errors.display_name}
        />

        {formError && (
          <p role="alert" className="text-sm text-danger">
            {formError}
          </p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-xl bg-linear-to-r from-cyan to-magenta px-4 py-3 text-sm font-semibold text-bg shadow-lg shadow-cyan/20 transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {pending ? 'Creating account...' : 'Create account'}
        </button>
      </form>

      <p className="my-4 text-center text-xs text-muted">or</p>

      <button
        type="button"
        onClick={onLogin}
        className="w-full rounded-xl border border-border bg-surface2 px-4 py-3 text-sm font-medium text-text transition-colors hover:border-muted"
      >
        I already have an account
      </button>
    </>
  )
}
