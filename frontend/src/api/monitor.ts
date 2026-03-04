import { api } from './client'
import type { EjecucionMonitor, ModoMonitor } from '@/types'

export const monitorApi = {
  async run(modo: ModoMonitor, notificar = false): Promise<{ run_id: number; mensaje: string }> {
    const { data } = await api.post('/monitor/run', { modo, notificar })
    return data
  },
  async getRun(id: number): Promise<EjecucionMonitor> {
    const { data } = await api.get<EjecucionMonitor>(`/monitor/runs/${id}`)
    return data
  },
  async listRuns(page = 1, limit = 10): Promise<EjecucionMonitor[]> {
    const { data } = await api.get<EjecucionMonitor[]>('/monitor/runs', {
      params: { page, limit },
    })
    return data
  },
}
