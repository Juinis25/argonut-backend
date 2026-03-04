import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from '@/hooks/useAuth'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { MarcasPage } from '@/pages/MarcasPage'
import { AlertasPage } from '@/pages/AlertasPage'
import { MonitorPage } from '@/pages/MonitorPage'

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#fff',
              color: '#1c1917',
              border: '1px solid #e7e5e4',
              borderRadius: '12px',
              fontSize: '14px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
            },
            success: {
              iconTheme: { primary: '#f59e0b', secondary: '#fff' },
            },
          }}
        />
        <Routes>
          {/* Públicas */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protegidas */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/marcas" element={<MarcasPage />} />
            <Route path="/alertas" element={<AlertasPage />} />
            <Route path="/monitor" element={<MonitorPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
