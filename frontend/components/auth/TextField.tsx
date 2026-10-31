interface TextFieldProps {
  label: string
  name: string
  type?: string
  placeholder?: string
  autoComplete?: string
  required?: boolean
  defaultValue?: string
  errors?: string[]
}

export default function TextField({ label, name, errors = [], ...input }: TextFieldProps) {
  const errorId = `${name}-error`
  const hasErrors = errors.length > 0

  return (
    <div>
      <label htmlFor={name} className="mb-2 block text-xs text-muted">
        {label}
      </label>
      <input
        id={name}
        name={name}
        aria-invalid={hasErrors}
        aria-describedby={hasErrors ? errorId : undefined}
        className={`w-full rounded-xl border bg-surface2 px-4 py-3 text-sm text-text outline-none placeholder:text-muted focus:border-cyan ${
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
