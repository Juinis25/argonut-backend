import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { alertasApi } from '@/api/alertas'
import { marcasApi } from '@/api/marcas'
import { monitorApi } from '@/api/monitor'
import { Card } from '@/components/ui/Card'
import { NivelBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/utils/format'
import type { Alerta, Marca, EjecucionMonitor } from '@/types'
import {
  Shield, Bell, Activity, TrendingUp, AlertTriangle,
  ArrowRight, CheckCircle2, Clock,
} from 'lucide-react'

export function DashboardPage() {
  const { user } = useAuth()
  const [marcas, setMarcas] = useState<Marca[]>([])
  const [alertas, setAlertas] = useState<Alerta[]>([])
  const [ultimaEjecucion, setUltimaEjecucion] = useState<EjecucionMonitor | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      marcasApi.list(),
      alertasApi.list({ resuelta: false, limit: 5 }),
      monitorApi.listRuns(1, 1),
    ]).then(([m, a, runs]) => {
      setMarcas(m)
      setAlertas(a)
      setUltimaEjecucion(runs[0] ?? null)
    }).finally(() => setLoading(false))
  }, [])

  const criticas = alertas.filter((a) => a.nivel === 'critica').length
  const altas = alertas.filter((a) => a.nivel === 'alta').length

  const stats = [
    {
      label: 'Marcas activas',
      value: loading ? '—' : marcas.length,
      icon: Shield,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      to: '/marcas',
    },
    {
      label: 'Alertas abiertas',
      value: loading ? '—' : alertas.length,
      icon: Bell,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
      to: '/alertas',
    },
    {
      label: 'Alertas críticas',
      value: loading ? '—' : criticas,
      icon: AlertTriangle,
      color: 'text-red-600',
      bg: 'bg-red-50',
      to: '/alertas?nivel=critica',
    },
    {
      label: 'Último monitoreo',
      value: loading ? '—' : (ultimaEjecucion ? formatDateTime(ultimaEjecucion.iniciada_el).split(',')[0] : 'Nunca'),
      icon: Activity,
      color: 'text-stone-600',
      bg: 'bg-stone-50',
      to: '/monitor',
    },
  ]

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-stone-800">
          Buen día, {user?.nombre?.split(' ')[0] ?? 'Usuario'} 👋
        </h1>
        <p className="text-stone-400 mt-1 text-sm">
          {new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, color, bg, to }) => (
          <Link key={label} to={to}>
            <Card className="p-5 hover:shadow-md hover:shadow-stone-100 hover:-translate-y-0.5 cursor-pointer group">
              <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center mb-3`}>
                <Icon size={20} className={color} />
              </div>
              <p className="text-2xl font-bold text-stone-800">{value}</p>
              <p className="text-xs text-stone-400 mt-0.5">{label}</p>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Alertas recientes */}
        <Card>
          <div className="px-6 py-4 border-b border-stone-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell size={16} className="text-stone-400" />
              <h2 className="font-semibold text-stone-700 text-sm">Alertas recientes</h2>
              {criticas > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-red-500 text-white text-[10px] font-bold">
                  {criticas}
                </span>
              )}
            </div>
            <Link to="/alertas" className="text-xs text-amber-600 hover:text-amber-700 flex items-center gap-1">
              Ver todas <ArrowRight size={12} />
            </Link>
          </div>
          <div className="divide-y divide-stone-50">
            {loading ? (
              <div className="px-6 py-8 text-center text-stone-300 text-sm">Cargando...</div>
            ) : alertas.length === 0 ? (
              <div className="px-6 py-8 text-center">
                <CheckCircle2 size={32} className="text-green-300 mx-auto mb-2" />
                <p className="text-sm text-stone-400">Sin alertas abiertas</p>
              </div>
            ) : (
              alertas.slice(0, 5).map((a) => (
                <div key={a.id} className="px-6 py-3.5 flex items-start gap-3 hover:bg-stone-50/50">
                  <NivelBadge nivel={a.nivel} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-stone-700 truncate">{a.solicitud_nombre}</p>
                    <p className="text-xs text-stone-400">
                      {a.expediente ? `Exp. ${a.expediente} · ` : ''}
                      {a.clase ? `Clase ${a.clase}` : ''}
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-stone-500 flex-shrink-0">
                    {Math.round(a.score)}%
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Mis marcas */}
        <Card>
          <div className="px-6 py-4 border-b border-stone-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-stone-400" />
              <h2 className="font-semibold text-stone-700 text-sm">Marcas vigiladas</h2>
            </div>
            <Link to="/marcas" className="text-xs text-amber-600 hover:text-amber-700 flex items-center gap-1">
              Gestionar <ArrowRight size={12} />
            </Link>
          </div>
          <div className="px-6 py-4 space-y-3">
            {loading ? (
              <p className="text-sm text-stone-300 text-center py-4">Cargando...</p>
            ) : marcas.length === 0 ? (
              <div className="text-center py-6">
                <Shield size={32} className="text-stone-200 mx-auto mb-2" />
                <p className="text-sm text-stone-400 mb-3">Todavía no registraste marcas</p>
                <Link to="/marcas">
                  <Button size="sm" variant="secondary">Agregar primera marca</Button>
                </Link>
              </div>
            ) : (
              marcas.map((m) => (
                <div key={m.id} className="flex items-center gap-3 p-3 rounded-xl bg-stone-50/60 hover:bg-stone-50">
                  <div className="w-9 h-9 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-bold text-amber-700">{m.clase}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-stone-700">{m.nombre}</p>
                    <p className="text-xs text-stone-400 truncate">{m.titular ?? 'Sin titular'}</p>
                  </div>
                  <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" title="Activa" />
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Estado del monitor */}
        {ultimaEjecucion && (
          <Card className="lg:col-span-2">
            <div className="px-6 py-4 border-b border-stone-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-stone-400" />
                <h2 className="font-semibold text-stone-700 text-sm">Última ejecución del monitor</h2>
              </div>
              <Link to="/monitor" className="text-xs text-amber-600 hover:text-amber-700 flex items-center gap-1">
                Ver historial <ArrowRight size={12} />
              </Link>
            </div>
            <div className="px-6 py-4 flex flex-wrap gap-6">
              <div className="flex items-center gap-2">
                <Clock size={14} className="text-stone-300" />
                <span className="text-sm text-stone-500">{formatDateTime(ultimaEjecucion.iniciada_el)}</span>
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp size={14} className="text-stone-300" />
                <span className="text-sm text-stone-500">{ultimaEjecucion.alertas_nuevas} nuevas alertas</span>
              </div>
              <div className="flex items-center gap-2">
                <AlertTriangle size={14} className="text-stone-300" />
                <span className="text-sm text-stone-500">{ultimaEjecucion.marcas_vigiladas} marcas vigiladas</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                ultimaEjecucion.estado === 'completado' ? 'bg-green-100 text-green-700' :
                ultimaEjecucion.estado === 'error' ? 'bg-red-100 text-red-700' :
                'bg-amber-100 text-amber-700'
              }`}>
                {ultimaEjecucion.estado}
              </span>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
