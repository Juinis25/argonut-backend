import { Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Sidebar } from './Sidebar'
import { Loader2 } from 'lucide-react'

export function AppLayout() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fffbf5]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-200">
            <Loader2 className="animate-spin text-white" size={20} />
          </div>
          <p className="text-sm text-stone-400">Cargando...</p>
        </div>
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="flex min-h-screen bg-[#fffbf5]">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
