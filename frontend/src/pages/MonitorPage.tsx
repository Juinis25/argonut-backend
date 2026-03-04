import { useEffect, useRef, useState } from 'react'
import { monitorApi } from '@/api/monitor'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/utils/format'
import type { EjecucionMonitor, EstadoEjecucion, ModoMonitor } from '@/types'
import {
  Activity, CheckCircle2, XCircle, Clock, Loader2,
  PlayCircle, AlertTriangle, ChevronDown, Bell, BellOff,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { cn } from '@/utils/cn'

// Mapeamos los estados reales del backend: 'corriendo' | 'completado' | 'error'
const ESTADO_CONFIG: Record<EstadoEjecucion, {
  icon: React.ElementType
  label: string
  className: string
  spin?: boolean
}> = {
  corriendo:  { icon: Loader2,      label: 'En curso',    className: 'text-amber-500', spin: true },
  completado: { icon: CheckCircle2, label: 'Completado',  className: 'text-green-500' },
  error:      { icon: XCircle,      label: 'Error',       className: 'text-red-500' },
}

function EstadoBadge({ estado }: { estado: EstadoEjecucion }) {
  const cfg = ESTADO_CONFIG[estado] ?? ESTADO_CONFIG.error
  const Icon = cfg.icon
  return (
    <span className={cn('flex items-center gap-1.5 text-xs font-medium', cfg.className)}>
      <Icon size={13} className={cfg.spin ? 'animate-spin' : ''} />
      {cfg.label}
    </span>
  )
}

const isTerminal = (estado: EstadoEjecucion) =>
  estado === 'completado' || estado === 'error'

export function MonitorPage() {
  const [runs, setRuns] = useState<EjecucionMonitor[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [activeRun, setActiveRun] = useState<EjecucionMonitor | null>(null)
  const [modo, setModo] = useState<ModoMonitor>('demo')
  const [notificar, setNotificar] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadRuns = async () => {
    try {
      const data = await monitorApi.listRuns(1, 10)
      setRuns(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRuns()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const startPolling = (id: number) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const run = await monitorApi.getRun(id)
        setActiveRun(run)
        if (isTerminal(run.estado)) {
          clearInterval(pollRef.current!)
          setRunning(false)
          setRuns((prev) => {
            const idx = prev.findIndex((r) => r.id === run.id)
            if (idx >= 0) {
              const next = [...prev]
              next[idx] = run
              return next
            }
            return [run, ...prev]
          })
          if (run.estado === 'completado') {
            toast.success(
              `Monitor completado · ${run.alertas_nuevas} alerta${run.alertas_nuevas !== 1 ? 's' : ''} nueva${run.alertas_nuevas !== 1 ? 's' : ''}`
            )
          } else {
            toast.error('La ejecución terminó con errores')
          }
        }
      } catch {
        // silent — seguimos intentando
      }
    }, 2000)
  }

  const handleRun = async () => {
    setRunning(true)
    setActiveRun(null)
    try {
      const { run_id } = await monitorApi.run(modo, notificar)
      // Cargamos el run recién creado
      const run = await monitorApi.getRun(run_id)
      setActiveRun(run)
      setRuns((prev) => [run, ...prev])
      startPolling(run_id)
      toast('Monitor iniciado', { icon: '🚀' })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg ?? 'Error al iniciar el monitor')
      setRunning(false)
    }
  }

  const progressPct = activeRun
    ? activeRun.marcas_vigiladas > 0
      ? Math.round(
          (activeRun.estado === 'completado' ? activeRun.marcas_vigiladas : 0) /
          activeRun.marcas_vigiladas * 100
        )
      : 0
    : 0

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-stone-800">Monitor</h1>
        <p className="text-stone-400 text-sm mt-1">Ejecutá una búsqueda de conflictos en INPI</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        {/* Panel de control */}
        <div className="lg:col-span-1">
          <Card>
            <div className="px-5 py-4 border-b border-stone-100">
              <h2 className="font-semibold text-stone-700 text-sm">Configuración</h2>
            </div>
            <div className="px-5 py-4 space-y-4">
              {/* Modo */}
              <div>
                <label className="text-xs font-medium text-stone-500 mb-2 block uppercase tracking-wide">
                  Modo de búsqueda
                </label>
                <div className="flex gap-2">
                  {(['demo', 'real'] as ModoMonitor[]).map((m) => (
                    <button
                      key={m}
                      onClick={() => setModo(m)}
                      className={cn(
                        'flex-1 py-2 rounded-xl text-sm font-medium border transition-all',
                        modo === m
                          ? 'bg-amber-500 text-white border-amber-500 shadow-sm'
                          : 'bg-white text-stone-500 border-stone-200 hover:border-amber-300'
                      )}
                    >
                      {m === 'demo' ? '🧪 Demo' : '🔴 Real'}
                    </button>
                  ))}
                </div>
                {modo === 'demo' && (
                  <p className="text-[11px] text-stone-400 mt-2 leading-relaxed">
                    Usa datos simulados. Ideal para probar sin consumir el servicio de INPI.
                  </p>
                )}
                {modo === 'real' && (
                  <p className="text-[11px] text-amber-600 mt-2 leading-relaxed">
                    Consulta real a INPI. Procesará todas tus marcas activas.
                  </p>
                )}
              </div>

              {/* Notificaciones */}
              <div>
                <label className="text-xs font-medium text-stone-500 mb-2 block uppercase tracking-wide">
                  Notificaciones
                </label>
                <button
                  onClick={() => setNotificar(!notificar)}
                  className={cn(
                    'w-full flex items-center gap-2 py-2 px-3 rounded-xl text-sm font-medium border transition-all',
                    notificar
                      ? 'bg-green-50 text-green-700 border-green-200'
                      : 'bg-white text-stone-400 border-stone-200 hover:border-stone-300'
                  )}
                >
                  {notificar ? <Bell size={14} /> : <BellOff size={14} />}
                  {notificar ? 'Notificar alertas nuevas' : 'Sin notificaciones'}
                </button>
              </div>

              {/* Botón ejecutar */}
              <Button
                onClick={handleRun}
                loading={running}
                disabled={running}
                className="w-full"
                size="md"
              >
                <PlayCircle size={16} />
                {running ? 'Ejecutando...' : 'Ejecutar monitor'}
              </Button>
            </div>
          </Card>
        </div>

        {/* Panel de progreso */}
        <div className="lg:col-span-2">
          {activeRun ? (
            <Card>
              <div className="px-5 py-4 border-b border-stone-100 flex items-center justify-between">
                <h2 className="font-semibold text-stone-700 text-sm">Ejecución en curso</h2>
                <EstadoBadge estado={activeRun.estado} />
              </div>
              <div className="px-5 py-5 space-y-4">
                {/* Barra de progreso */}
                <div>
                  <div className="flex justify-between text-xs text-stone-400 mb-1.5">
                    <span>{activeRun.marcas_vigiladas} marcas totales</span>
                    <span>{activeRun.estado === 'completado' ? '100' : progressPct}%</span>
                  </div>
                  <div className="h-2 bg-stone-100 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-700',
                        activeRun.estado === 'completado'
                          ? 'bg-gradient-to-r from-green-400 to-emerald-400'
                          : activeRun.estado === 'error'
                          ? 'bg-red-400'
                          : 'bg-gradient-to-r from-amber-400 to-orange-400 animate-pulse'
                      )}
                      style={{ width: `${activeRun.estado === 'completado' ? 100 : activeRun.estado === 'corriendo' ? 60 : 20}%` }}
                    />
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-stone-50 rounded-xl p-3 text-center">
                    <p className="text-2xl font-bold text-stone-800">{activeRun.marcas_vigiladas}</p>
                    <p className="text-[11px] text-stone-400 mt-0.5">Marcas</p>
                  </div>
                  <div className="bg-amber-50 rounded-xl p-3 text-center">
                    <p className="text-2xl font-bold text-amber-700">{activeRun.alertas_nuevas}</p>
                    <p className="text-[11px] text-amber-400 mt-0.5">Alertas nuevas</p>
                  </div>
                </div>

                {/* Info */}
                <div className="text-xs text-stone-400 space-y-1">
                  <p>Iniciado: {formatDateTime(activeRun.iniciada_el)}</p>
                  {activeRun.finalizada_el && (
                    <p>Finalizado: {formatDateTime(activeRun.finalizada_el)}</p>
                  )}
                  {activeRun.error_msg && (
                    <div className="mt-2 p-2.5 bg-red-50 rounded-lg flex gap-2">
                      <AlertTriangle size={13} className="text-red-400 mt-0.5 flex-shrink-0" />
                      <p className="text-red-600 text-[11px] leading-relaxed">{activeRun.error_msg}</p>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-2xl bg-amber-50 flex items-center justify-center mx-auto mb-4">
                  <Activity size={28} className="text-amber-300" />
                </div>
                <h3 className="text-stone-600 font-medium mb-1">Sin ejecución activa</h3>
                <p className="text-stone-400 text-sm">Configurá y ejecutá el monitor para ver el progreso</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Historial */}
      <div>
        <h2 className="text-base font-semibold text-stone-700 mb-4">Historial</h2>
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="animate-spin text-amber-400" size={28} />
          </div>
        ) : runs.length === 0 ? (
          <div className="text-center py-12 text-stone-400 text-sm">
            Sin ejecuciones previas
          </div>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <Card key={run.id} className="overflow-hidden">
                <button
                  onClick={() => setExpandedId(expandedId === run.id ? null : run.id)}
                  className="w-full px-5 py-3.5 flex items-center gap-4 hover:bg-stone-50/80 transition-colors text-left"
                >
                  <EstadoBadge estado={run.estado} />
                  <span className="flex-1 text-sm text-stone-600">{formatDateTime(run.iniciada_el)}</span>
                  <div className="flex items-center gap-4 text-xs text-stone-400">
                    <span>{run.marcas_vigiladas} marcas</span>
                    {run.alertas_nuevas > 0 && (
                      <span className="text-amber-600 font-medium">{run.alertas_nuevas} alertas</span>
                    )}
                    <span className={cn(
                      'px-2 py-0.5 rounded-md font-medium',
                      run.modo === 'demo' ? 'bg-stone-100 text-stone-500' : 'bg-red-50 text-red-500'
                    )}>
                      {run.modo}
                    </span>
                  </div>
                  <ChevronDown
                    size={14}
                    className={cn('text-stone-300 transition-transform', expandedId === run.id && 'rotate-180')}
                  />
                </button>
                {expandedId === run.id && (
                  <div className="px-5 pb-4 border-t border-stone-50 bg-stone-50/50">
                    <div className="pt-3 grid grid-cols-2 gap-3 text-xs text-stone-500">
                      <div>
                        <span className="font-medium text-stone-600">Alertas nuevas:</span>{' '}
                        {run.alertas_nuevas}
                      </div>
                      <div>
                        <span className="font-medium text-stone-600">Expedientes procesados:</span>{' '}
                        {run.expedientes_proc}
                      </div>
                      {run.finalizada_el && (
                        <div>
                          <span className="font-medium text-stone-600">Finalizado:</span>{' '}
                          {formatDateTime(run.finalizada_el)}
                        </div>
                      )}
                      {run.error_msg && (
                        <div className="col-span-2">
                          <span className="font-medium text-red-500">Error:</span>{' '}
                          <span className="text-red-400">{run.error_msg}</span>
                        </div>
                      )}
                      {run.log_output && (
                        <div className="col-span-2">
                          <span className="font-medium text-stone-600 block mb-1">Logs:</span>
                          <div className="bg-stone-100 rounded-lg p-2 font-mono text-[10px] text-stone-500 max-h-24 overflow-y-auto">
                            {run.log_output.split('\n').map((line, i) => <p key={i}>{line}</p>)}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
