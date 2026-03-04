import { useEffect, useState } from 'react'
import { marcasApi } from '@/api/marcas'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useAuth } from '@/hooks/useAuth'
import { CLASE_NICE } from '@/utils/format'
import type { Marca, MarcaCreate } from '@/types'
import { Shield, Plus, Trash2, X, Loader2, Lock } from 'lucide-react'
import toast from 'react-hot-toast'

const PLAN_LIMITS: Record<string, number> = { free: 3, starter: 10, pro: Infinity }

const CLASES_POPULARES = [35, 42, 9, 25, 41, 43, 36, 44, 5, 30]

export function MarcasPage() {
  const { user } = useAuth()
  const [marcas, setMarcas] = useState<Marca[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<number | null>(null)

  const [form, setForm] = useState<MarcaCreate>({
    nombre: '', clase: 42, titular: '', contacto: '', notas: '',
  })

  const planLimit = PLAN_LIMITS[user?.plan ?? 'free']
  const canAdd = marcas.length < planLimit

  useEffect(() => {
    marcasApi.list().then(setMarcas).finally(() => setLoading(false))
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    try {
      const nueva = await marcasApi.create({ ...form, nombre: form.nombre.toUpperCase() })
      setMarcas((prev) => [...prev, nueva])
      setForm({ nombre: '', clase: 42, titular: '', contacto: '', notas: '' })
      setShowForm(false)
      toast.success(`Marca ${nueva.nombre} agregada`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg ?? 'Error al crear la marca')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: number, nombre: string) => {
    if (!confirm(`¿Eliminar la marca ${nombre}? Esta acción es irreversible.`)) return
    setDeleting(id)
    try {
      await marcasApi.delete(id)
      setMarcas((prev) => prev.filter((m) => m.id !== id))
      toast.success(`Marca ${nombre} eliminada`)
    } catch {
      toast.error('Error al eliminar la marca')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Mis marcas</h1>
          <p className="text-stone-400 text-sm mt-1">
            {marcas.length} de {planLimit === Infinity ? '∞' : planLimit} marcas en plan {user?.plan}
          </p>
        </div>
        {canAdd ? (
          <Button onClick={() => setShowForm(!showForm)} size="md">
            <Plus size={16} />
            Agregar marca
          </Button>
        ) : (
          <div className="flex items-center gap-2 text-sm text-stone-400">
            <Lock size={14} />
            Límite del plan alcanzado
          </div>
        )}
      </div>

      {/* Formulario inline */}
      {showForm && (
        <Card className="mb-6 border-amber-100">
          <div className="px-6 py-4 border-b border-amber-100/80 bg-amber-50/30 rounded-t-2xl flex items-center justify-between">
            <h2 className="font-semibold text-stone-700 text-sm">Nueva marca</h2>
            <button onClick={() => setShowForm(false)} className="text-stone-300 hover:text-stone-500">
              <X size={16} />
            </button>
          </div>
          <form onSubmit={handleCreate} className="px-6 py-5">
            <div className="grid grid-cols-2 gap-4 mb-4">
              <Input
                label="Nombre de la marca *"
                placeholder="ARGONUT"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value.toUpperCase() })}
                required
              />
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-stone-600">Clase NICE *</label>
                <select
                  value={form.clase}
                  onChange={(e) => setForm({ ...form, clase: Number(e.target.value) })}
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm bg-white border border-stone-200 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400/50 focus:border-amber-400"
                >
                  {Array.from({ length: 45 }, (_, i) => i + 1).map((c) => (
                    <option key={c} value={c}>
                      Clase {c} — {CLASE_NICE[c] ?? ''}
                    </option>
                  ))}
                </select>
              </div>
              <Input
                label="Titular"
                placeholder="Nombre o razón social"
                value={form.titular}
                onChange={(e) => setForm({ ...form, titular: e.target.value })}
              />
              <Input
                label="Contacto"
                placeholder="Email o teléfono"
                value={form.contacto}
                onChange={(e) => setForm({ ...form, contacto: e.target.value })}
              />
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancelar</Button>
              <Button type="submit" loading={creating}>Guardar marca</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Clases populares hint */}
      {showForm && (
        <div className="mb-6 flex flex-wrap gap-2">
          {CLASES_POPULARES.map((c) => (
            <button
              key={c}
              onClick={() => setForm({ ...form, clase: c })}
              className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                form.clase === c
                  ? 'bg-amber-500 text-white border-amber-500'
                  : 'bg-white text-stone-500 border-stone-200 hover:border-amber-300'
              }`}
            >
              Cl. {c} · {CLASE_NICE[c]?.split('/')[0]}
            </button>
          ))}
        </div>
      )}

      {/* Lista */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="animate-spin text-amber-400" size={32} />
        </div>
      ) : marcas.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-amber-50 flex items-center justify-center mx-auto mb-4">
            <Shield size={28} className="text-amber-300" />
          </div>
          <h3 className="text-stone-600 font-medium mb-1">Sin marcas registradas</h3>
          <p className="text-stone-400 text-sm mb-4">Agregá tu primera marca para empezar a monitorear</p>
          <Button onClick={() => setShowForm(true)} size="sm">
            <Plus size={14} /> Agregar primera marca
          </Button>
        </div>
      ) : (
        <div className="grid gap-3">
          {marcas.map((m) => (
            <Card key={m.id} className="hover:shadow-md hover:shadow-stone-100 transition-all">
              <div className="px-6 py-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-100 to-amber-200 flex flex-col items-center justify-center flex-shrink-0">
                  <span className="text-[10px] text-amber-500 font-medium leading-none">CL.</span>
                  <span className="text-lg font-bold text-amber-700 leading-tight">{m.clase}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-stone-800 tracking-wide">{m.nombre}</h3>
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  </div>
                  <p className="text-xs text-stone-400 mt-0.5 truncate">
                    {CLASE_NICE[m.clase] ?? `Clase ${m.clase}`}
                    {m.titular && ` · ${m.titular}`}
                  </p>
                </div>
                <div className="text-right text-xs text-stone-300 flex-shrink-0">
                  {m.contacto && <p className="mb-0.5">{m.contacto}</p>}
                </div>
                <button
                  onClick={() => handleDelete(m.id, m.nombre)}
                  disabled={deleting === m.id}
                  className="text-stone-200 hover:text-red-500 transition-colors p-1.5 rounded-lg hover:bg-red-50"
                >
                  {deleting === m.id ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
