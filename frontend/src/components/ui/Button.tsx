import { cn } from '@/utils/cn'
import { Loader2 } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

const variants = {
  primary: 'bg-amber-500 hover:bg-amber-600 text-white shadow-sm shadow-amber-200/50 border border-amber-400',
  secondary: 'bg-white hover:bg-stone-50 text-stone-700 border border-stone-200 shadow-sm',
  ghost: 'text-stone-600 hover:bg-stone-100 hover:text-stone-800',
  danger: 'bg-red-500 hover:bg-red-600 text-white shadow-sm',
}

const sizes = {
  sm: 'text-xs px-3 py-1.5 rounded-lg gap-1.5',
  md: 'text-sm px-4 py-2 rounded-xl gap-2',
  lg: 'text-base px-6 py-3 rounded-xl gap-2',
}

export function Button({
  variant = 'primary', size = 'md', loading, disabled,
  className, children, ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center font-medium transition-all',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-1',
        variants[variant], sizes[size], className
      )}
    >
      {loading && <Loader2 className="animate-spin" size={14} />}
      {children}
    </button>
  )
}
