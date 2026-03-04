import { cn } from '@/utils/cn'
import type { HTMLAttributes } from 'react'

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={cn(
        'bg-white rounded-2xl border border-stone-100 shadow-sm shadow-stone-100',
        className
      )}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div {...props} className={cn('px-6 py-4 border-b border-stone-100', className)}>
      {children}
    </div>
  )
}

export function CardBody({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div {...props} className={cn('px-6 py-4', className)}>
      {children}
    </div>
  )
}
