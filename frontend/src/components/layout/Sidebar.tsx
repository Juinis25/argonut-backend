import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { PlanBadge } from '@/components/ui/Badge'
import { cn } from '@/utils/cn'
import {
  LayoutDashboard, Shield, Bell, Activity,
  LogOut, ChevronRight, Zap,
} from 'lucide-react'

const nav = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/marcas', icon: Shield, label: 'Marcas' },
  { to: '/alertas', icon: Bell, label: 'Alertas' },
  { to: '/monitor', icon: Activity, label: 'Monitor' },
]

export function Sidebar() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <aside className="w-64 bg-white border-r border-stone-100 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-stone-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-sm">
            <Zap size={16} className="text-white" />
          </div>
          <div>
            <span className="text-lg font-bold text-stone-800 tracking-tight">Argonut</span>
            <span className="block text-[10px] text-stone-400 -mt-0.5 leading-none">Vigilancia de marcas</span>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {nav.map(({ to, icon: Icon, label }) => {
          const active = location.pathname.startsWith(to)
          return (
            <Link
              key={to}
              to={to}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group',
                active
                  ? 'bg-amber-50 text-amber-700 shadow-inner'
                  : 'text-stone-500 hover:bg-stone-50 hover:text-stone-800'
              )}
            >
              <Icon size={18} className={active ? 'text-amber-600' : 'text-stone-400 group-hover:text-stone-600'} />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight size={14} className="text-amber-400" />}
            </Link>
          )
        })}
      </nav>

      {/* User footer */}
      <div className="px-3 py-4 border-t border-stone-100">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-stone-50">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-300 to-amber-500 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-bold text-white uppercase">
              {user?.nombre?.[0] ?? user?.email?.[0] ?? '?'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-stone-800 truncate">{user?.nombre ?? 'Usuario'}</p>
            <PlanBadge plan={user?.plan ?? 'free'} />
          </div>
          <button onClick={handleLogout} className="text-stone-300 hover:text-red-500 transition-colors" title="Cerrar sesión">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
