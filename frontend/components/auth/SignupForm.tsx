'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, apiFetch, errorDetail, fieldErrors } from '@/lib/api'
import type { FieldErrors } from '@/lib/api'
import type { LoginPageLabels, Player, RegisterPayload } from '@/types/account'
import TextField from './TextField'

interface SignupFormProps {
  labels: LoginPageLabels
  onLogin: () => void
}

export default function SignupForm({ labels, onLogin }: SignupFormProps) {
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
      // The backend logs the new player in: the response sets the cookies.
      await apiFetch<Player>('/register', { method: 'POST', body: payload, auth: false })
      router.replace('/')
    } catch (error) {
      setPending(false)
      if (!(error instanceof ApiError)) throw error

      const fields = fieldErrors(error)
      setErrors(fields)
      if (!fields.email && !fields.password && !fields.display_name) {
        setFormError(errorDetail(error, labels.server_unreachable))
      }
    }
  }

  return (
    <>
      <h2 className="font-heading text-2xl font-bold">{labels.signup_title}</h2>
      <p className="mt-1 text-sm text-muted">{labels.signup_subtitle}</p>

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
          autoComplete="new-password"
          required
          errors={errors.password}
        />
        <TextField
          label={labels.display_name_label}
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
          {pending ? labels.signup_pending : labels.signup_button}
        </button>
      </form>

      <p className="my-4 text-center text-xs text-muted">{labels.or_text}</p>

      <button
        type="button"
        onClick={onLogin}
        className="w-full rounded-xl border border-border bg-surface2 px-4 py-3 text-sm font-medium text-text transition-colors hover:border-muted"
      >
        {labels.have_account_button}
      </button>
    </>
  )
}
