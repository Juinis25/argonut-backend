import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { alertasApi } from '@/api/alertas'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { NivelBadge } from '@/components/ui/Badge'
import { formatDateTime } from '@/utils/format'
import type { Alerta, NivelAlerta } from '@/types'
import { Bell, CheckCircle2, EyeOff, Filter, Loader2, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { cn } from '@/utils/cn'

const NIVELES: Array<{ value: NivelAlerta | 'all'; label: string }> = [
  { value: 'all', label: 'Todas' },
  { value: 'critica', label: 'Crítica' },
  { value: 'alta', label: 'Alta' },
  { value: 'media', label: 'Media' },
  { value: 'baja', label: 'Baja' },
]

export function AlertasPage() {
  const [searchParams] = useSearchParams()
  const [alertas, setAlertas] = useState<Alerta[]>([])
  const [loading, setLoading] = useState(true)
  const [resolving, setResolving] = useState<number | null>(null)
  const [nivelFilter, setNivelFilter] = useState<NivelAlerta | 'all'>(
    (searchParams.get('nivel') as NivelAlerta) ?? 'all'
  )
  const [showResueltas, setShowResueltas] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await alertasApi.list({
        resuelta: showResueltas ? undefined : false,
        nivel: nivelFilter !== 'all' ? nivelFilter : undefined,
        limit: 100,
      })
      setAlertas(data)
    } finally {
      setLoading(false)
    }
  }, [nivelFilter, showResueltas])

  useEffect(() => { load() }, [load])

  const handleResolver = async (id: number) => {
    setResolving(id)
    try {
      await alertasApi.resolver(id)
      setAlertas((prev) => prev.filter((a) => a.id !== id))
      toast.success('Alerta marcada como resuelta')
    } catch {
      toast.error('Error al resolver la alerta')
    } finally {
      setResolving(null)
    }
  }

  const handleIgnorar = async (id: number) => {
    setResolving(id)
    try {
      await alertasApi.ignorar(id)
      setAlertas((prev) => prev.filter((a) => a.id !== id))
      toast('Alerta ignorada', { icon: '👁' })
    } catch {
      toast.error('Error al ignorar la alerta')
    } finally {
      setResolving(null)
    }
  }

  const criticas = alertas.filter((a) => a.nivel === 'critica').length
  const altas = alertas.filter((a) => a.nivel === 'alta').length

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Alertas</h1>
          <p className="text-stone-400 text-sm mt-1">
            {alertas.length} alerta{alertas.length !== 1 ? 's' : ''}
            {criticas > 0 && <span className="text-red-500 font-medium"> · {criticas} crítica{criticas > 1 ? 's' : ''}</span>}
            {altas > 0 && <span className="text-orange-500 font-medium"> · {altas} alta{altas > 1 ? 's' : ''}</span>}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={load}>
          <RefreshCw size={13} />
          Actualizar
        </Button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex items-center gap-1.5 bg-white rounded-xl p-1 border border-stone-200 shadow-sm">
          {NIVELES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setNivelFilter(value)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                nivelFilter === value
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'text-stone-500 hover:text-stone-700 hover:bg-stone-50'
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          onClick={() => setShowResueltas(!showResueltas)}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium border transition-all',
            showResueltas
              ? 'bg-stone-700 text-white border-stone-700'
              : 'bg-white text-stone-500 border-stone-200 hover:border-stone-300'
          )}
        >
          <Filter size={13} />
          {showResueltas ? 'Ver abiertas' : 'Ver resueltas'}
        </button>
      </div>

      {/* Lista */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="animate-spin text-amber-400" size={32} />
        </div>
      ) : alertas.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-green-50 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 size={28} className="text-green-400" />
          </div>
          <h3 className="text-stone-600 font-medium mb-1">Sin alertas</h3>
          <p className="text-stone-400 text-sm">No hay alertas en esta categoría</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alertas.map((a) => (
            <Card
              key={a.id}
              className={cn(
                'hover:shadow-md transition-all',
                a.nivel === 'critica' && 'border-red-100',
                a.nivel === 'alta' && 'border-orange-100',
                a.resuelta && 'opacity-60'
              )}
            >
              <div className="px-6 py-4">
                <div className="flex items-start gap-4">
                  {/* Score visual */}
                  <div className="flex-shrink-0 text-center">
                    <div className={cn(
                      'w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm',
                      a.nivel === 'critica' ? 'bg-red-100 text-red-700' :
                      a.nivel === 'alta' ? 'bg-orange-100 text-orange-700' :
                      a.nivel === 'media' ? 'bg-amber-100 text-amber-700' :
                      'bg-green-100 text-green-700'
                    )}>
                      {Math.round(a.score)}%
                    </div>
                    <p className="text-[10px] text-stone-300 mt-1">similitud</p>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <NivelBadge nivel={a.nivel} />
                      {a.clase && <span className="text-xs text-stone-400">Clase {a.clase}</span>}
                      {a.expediente && (
                        <span className="text-xs text-stone-300">· Exp. {a.expediente}</span>
                      )}
                    </div>
                    <h3 className="font-semibold text-stone-800 text-sm">{a.solicitud_nombre}</h3>
                    <p className="text-xs text-stone-400 mt-0.5">
                      Titular: {a.titular_solicitante ?? '—'}
                    </p>
                    <p className="text-[11px] text-stone-300 mt-1">{formatDateTime(a.detectado_el)}</p>
                  </div>

                  {!a.resuelta && (
                    <div className="flex gap-2 flex-shrink-0">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleIgnorar(a.id)}
                        loading={resolving === a.id}
                        className="text-stone-400 hover:text-stone-600"
                      >
                        <EyeOff size={14} />
                        Ignorar
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleResolver(a.id)}
                        loading={resolving === a.id}
                      >
                        <CheckCircle2 size={14} />
                        Resolver
                      </Button>
                    </div>
                  )}
                  {a.resuelta && (
                    <span className="text-xs text-green-600 font-medium flex items-center gap-1 flex-shrink-0">
                      <CheckCircle2 size={13} /> Resuelta
                    </span>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
