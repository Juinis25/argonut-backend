// === AUTH ===
export interface User {
  id: number
  email: string
  nombre: string
  plan: 'free' | 'starter' | 'pro'
  is_active: boolean
  is_verified: boolean
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

// === MARCAS ===
export interface Marca {
  id: number
  nombre: string
  clase: number
  titular?: string
  contacto?: string
  notas?: string
  activa: boolean
  created_at: string
}

export interface MarcaCreate {
  nombre: string
  clase: number
  titular?: string
  contacto?: string
  notas?: string
}

// === ALERTAS ===
export type NivelAlerta = 'critica' | 'alta' | 'media' | 'baja'

export interface Alerta {
  id: number
  marca_id: number
  marca_nombre?: string
  clase?: number                  // clase de la marca vigilada (join desde backend)
  expediente?: string
  solicitud_nombre: string        // nombre de la solicitud/marca conflictante
  titular_solicitante?: string    // titular de la solicitud conflictante
  fecha_solicitud?: string
  score: number                   // 0–100 (entero de fuzzywuzzy)
  nivel: NivelAlerta
  metodo?: string
  scores_detalle?: Record<string, number>
  notificada: boolean
  resuelta: boolean
  notas_resolucion?: string
  detectado_el: string            // ISO datetime
}

// === MONITOR ===
export type ModoMonitor = 'demo' | 'real'
export type EstadoEjecucion = 'corriendo' | 'completado' | 'error'

export interface EjecucionMonitor {
  id: number
  modo: ModoMonitor
  estado: EstadoEjecucion
  marcas_vigiladas: number
  alertas_nuevas: number
  expedientes_proc: number
  error_msg?: string
  iniciada_el: string             // ISO datetime
  finalizada_el?: string          // ISO datetime
  log_output?: string             // string plano, no array
}

// === API RESPONSE ===
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pages: number
}
