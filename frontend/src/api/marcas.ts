import { api } from './client'
import type { Marca, MarcaCreate } from '@/types'

export const marcasApi = {
  async list(): Promise<Marca[]> {
    const { data } = await api.get<Marca[]>('/marcas/')
    return data
  },
  async create(payload: MarcaCreate): Promise<Marca> {
    const { data } = await api.post<Marca>('/marcas/', payload)
    return data
  },
  async delete(id: number): Promise<void> {
    await api.delete(`/marcas/${id}`)
  },
}
