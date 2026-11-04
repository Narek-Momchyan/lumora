'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import type { FormEvent } from 'react'
import Button from '@/components/ui/Button'
import Field from '@/components/ui/Field'
import { ApiError, apiFetch, errorDetail, fieldErrors } from '@/lib/api'
import type { FieldErrors } from '@/lib/api'
import type { LoginPageLabels, Player, RegisterPayload } from '@/types/account'

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
        <Field
          id="email"
          name="email"
          label={labels.email_label}
          type="email"
          placeholder={labels.email_placeholder}
          autoComplete="email"
          required
          errors={errors.email}
        />
        <Field
          id="password"
          name="password"
          label={labels.password_label}
          type="password"
          autoComplete="new-password"
          required
          errors={errors.password}
        />
        <Field
          id="display_name"
          name="display_name"
          label={labels.display_name_label}
          autoComplete="nickname"
          errors={errors.display_name}
        />

        {formError && (
          <p role="alert" className="text-sm text-danger">
            {formError}
          </p>
        )}

        <Button type="submit" disabled={pending} size="lg" block>
          {pending ? labels.signup_pending : labels.signup_button}
        </Button>
      </form>

      <p className="my-4 text-center text-xs text-muted">{labels.or_text}</p>

      <Button variant="ghost" size="lg" block onClick={onLogin}>
        {labels.have_account_button}
      </Button>
    </>
  )
}
