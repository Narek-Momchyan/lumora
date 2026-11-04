'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import type { FormEvent } from 'react'
import Button from '@/components/ui/Button'
import Field from '@/components/ui/Field'
import { ApiError, errorDetail, fieldErrors, login } from '@/lib/api'
import type { FieldErrors } from '@/lib/api'
import type { LoginPageLabels } from '@/types/account'

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
          autoComplete="current-password"
          required
          errors={errors.password}
        />

        {formError && (
          <p role="alert" className="text-sm text-danger">
            {formError}
          </p>
        )}

        <Button type="submit" disabled={pending} size="lg" block>
          {pending ? labels.login_pending : labels.login_button}
        </Button>
      </form>

      <p className="my-4 text-center text-xs text-muted">{labels.or_text}</p>

      <Button variant="ghost" size="lg" block onClick={onCreateAccount}>
        {labels.create_account_button}
      </Button>
    </>
  )
}
