import { cn } from '@/utils/cn'
import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export function Input({ label, error, hint, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-sm font-medium text-stone-600">{label}</label>
      )}
      <input
        {...props}
        className={cn(
          'w-full px-3.5 py-2.5 rounded-xl text-sm',
          'bg-white border border-stone-200',
          'placeholder:text-stone-400 text-stone-800',
          'focus:outline-none focus:ring-2 focus:ring-amber-400/50 focus:border-amber-400',
          'transition-colors',
          error && 'border-red-300 focus:ring-red-200 focus:border-red-400',
          className
        )}
      />
      {error && <span className="text-xs text-red-500">{error}</span>}
      {hint && !error && <span className="text-xs text-stone-400">{hint}</span>}
    </div>
  )
}
