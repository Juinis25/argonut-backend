import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Zap, Check } from 'lucide-react'
import toast from 'react-hot-toast'

export function RegisterPage() {
  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.length < 8) { toast.error('La contraseña debe tener al menos 8 caracteres'); return }
    setLoading(true)
    try {
      await register(email, password, nombre)
      toast.success('¡Cuenta creada! Bienvenido a Argonut.')
      navigate('/dashboard')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg ?? 'Error al crear la cuenta')
    } finally {
      setLoading(false)
    }
  }

  const features = [
    'Monitoreo automático contra INPI',
    'Alertas por email en tiempo real',
    'Panel de gestión de marcas',
  ]

  return (
    <div className="min-h-screen bg-[#fffbf5] flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-amber-100/40 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-orange-100/30 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-200/60 mb-4">
            <Zap size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-stone-800">Crear cuenta</h1>
          <p className="text-stone-400 text-sm mt-1">Gratis · Sin tarjeta de crédito</p>
        </div>

        {/* Features */}
        <div className="bg-amber-50/60 rounded-xl p-4 mb-6 border border-amber-100">
          <ul className="space-y-1.5">
            {features.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-amber-800">
                <Check size={14} className="text-amber-600 flex-shrink-0" />
                {f}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white rounded-2xl border border-stone-100 shadow-sm p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <Input label="Nombre" type="text" placeholder="Tu nombre o empresa" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
            <Input label="Email" type="email" placeholder="tu@empresa.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <Input
              label="Contraseña"
              type="password"
              placeholder="Mínimo 8 caracteres"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              hint="Al menos 8 caracteres"
            />
            <Button type="submit" className="w-full" size="lg" loading={loading}>
              Crear cuenta gratis
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-stone-400 mt-6">
          ¿Ya tenés cuenta?{' '}
          <Link to="/login" className="text-amber-600 hover:text-amber-700 font-medium">
            Iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  )
}
