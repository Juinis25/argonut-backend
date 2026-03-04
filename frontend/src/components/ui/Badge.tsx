import { cn } from '@/utils/cn'
import type { NivelAlerta } from '@/types'

const nivelStyles: Record<NivelAlerta, string> = {
  critica: 'bg-red-100 text-red-700 border-red-200',
  alta: 'bg-orange-100 text-orange-700 border-orange-200',
  media: 'bg-amber-100 text-amber-700 border-amber-200',
  baja: 'bg-green-100 text-green-700 border-green-200',
}

const nivelDot: Record<NivelAlerta, string> = {
  critica: 'bg-red-500',
  alta: 'bg-orange-500',
  media: 'bg-amber-500',
  baja: 'bg-green-500',
}

export function NivelBadge({ nivel }: { nivel: NivelAlerta }) {
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border', nivelStyles[nivel])}>
      <span className={cn('w-1.5 h-1.5 rounded-full', nivelDot[nivel])} />
      {nivel.charAt(0).toUpperCase() + nivel.slice(1)}
    </span>
  )
}

export function PlanBadge({ plan }: { plan: string }) {
  const styles: Record<string, string> = {
    free: 'bg-stone-100 text-stone-600',
    starter: 'bg-amber-100 text-amber-700',
    pro: 'bg-gradient-to-r from-amber-100 to-orange-100 text-orange-700',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide', styles[plan] ?? styles.free)}>
      {plan}
    </span>
  )
}
