import type { InputHTMLAttributes } from 'react'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string
  label: string
  errors?: string[]
}

// A label over an input, with the field's errors from the API under it.
export default function Field({ id, label, errors = [], className = '', ...input }: FieldProps) {
  const errorId = `${id}-error`
  const hasErrors = errors.length > 0

  return (
    <div className={`min-w-0 ${className}`}>
      <label htmlFor={id} className="mb-2 block truncate text-xs text-muted lg:text-[13px]">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={hasErrors}
        aria-describedby={hasErrors ? errorId : undefined}
        className={`h-11 w-full rounded-xl border bg-surface2 px-4 text-sm text-text outline-none placeholder:text-muted focus:border-accent lg:h-12 lg:text-[15px] ${
          hasErrors ? 'border-danger' : 'border-border'
        }`}
        {...input}
      />
      {hasErrors && (
        <ul id={errorId} className="mt-2 space-y-1 text-xs text-danger">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
