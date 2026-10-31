'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, errorDetail, fieldErrors, login } from '@/lib/api'
import type { FieldErrors } from '@/lib/api'
import type { LoginPageLabels } from '@/types/account'
import TextField from './TextField'

interface LoginFormProps {
  labels: LoginPageLabels
  onCreateAccount: () => void
}

export default function LoginForm({ labels, onCreateAccount }: LoginFormProps) {
  const router = useRouter()
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)

    setPending(true)
    setErrors({})
    setFormError('')

    try {
      await login(String(form.get('email')), String(form.get('password')))
      router.replace('/')
    } catch (error) {
      setPending(false)
      if (!(error instanceof ApiError)) throw error

      const fields = fieldErrors(error)
      setErrors(fields)
      if (!fields.email && !fields.password) setFormError(errorDetail(error, labels.server_unreachable))
    }
  }

  return (
    <>
      <h2 className="font-heading text-2xl font-bold">{labels.login_title}</h2>
      <p className="mt-1 text-sm text-muted">{labels.login_subtitle}</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <TextField
          label={labels.email_label}
          name="email"
          type="email"
          placeholder={labels.email_placeholder}
          autoComplete="email"
          required
          errors={errors.email}
        />
        <TextField
          label={labels.password_label}
          name="password"
          type="password"
          autoComplete="current-password"
          required
          errors={errors.password}
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
          {pending ? labels.login_pending : labels.login_button}
        </button>
      </form>

      <p className="my-4 text-center text-xs text-muted">{labels.or_text}</p>

      <button
        type="button"
        onClick={onCreateAccount}
        className="w-full rounded-xl border border-border bg-surface2 px-4 py-3 text-sm font-medium text-text transition-colors hover:border-muted"
      >
        {labels.create_account_button}
      </button>
    </>
  )
}
