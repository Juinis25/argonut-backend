import { api } from './client'
import type { Alerta, NivelAlerta } from '@/types'

interface AlertaFilters {
  resuelta?: boolean
  nivel?: NivelAlerta
  marca_id?: number
  page?: number
  limit?: number
}

export const alertasApi = {
  async list(filters: AlertaFilters = {}): Promise<Alerta[]> {
    const { data } = await api.get<Alerta[]>('/alertas/', { params: filters })
    return data
  },
  async resolver(id: number, notas?: string): Promise<Alerta> {
    const { data } = await api.post<Alerta>(`/alertas/${id}/resolver`, { notas })
    return data
  },
  async ignorar(id: number): Promise<Alerta> {
    const { data } = await api.post<Alerta>(`/alertas/${id}/ignorar`)
    return data
  },
}
