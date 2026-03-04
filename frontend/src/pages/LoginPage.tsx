import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Zap, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg ?? 'Credenciales incorrectas')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#fffbf5] flex items-center justify-center p-4">
      {/* Decoración fondo */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-amber-100/40 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-orange-100/30 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-200/60 mb-4">
            <Zap size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-stone-800">Bienvenido a Argonut</h1>
          <p className="text-stone-400 text-sm mt-1">Tu sistema de vigilancia de marcas</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-stone-100 shadow-sm shadow-stone-100 p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              label="Email"
              type="email"
              placeholder="tu@empresa.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-stone-600">Contraseña</label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl text-sm bg-white border border-stone-200 placeholder:text-stone-400 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400/50 focus:border-amber-400 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <Button type="submit" className="w-full" size="lg" loading={loading}>
              Iniciar sesión
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-stone-400 mt-6">
          ¿No tenés cuenta?{' '}
          <Link to="/register" className="text-amber-600 hover:text-amber-700 font-medium">
            Registrate gratis
          </Link>
        </p>
      </div>
    </div>
  )
}
