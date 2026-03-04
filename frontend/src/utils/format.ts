export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatScore(score: number): string {
  return `${Math.round(score)}%`
}

export const NIVEL_COLORS = {
  critica: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', dot: 'bg-red-500' },
  alta: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500' },
  media: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-500' },
  baja: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', dot: 'bg-green-500' },
} as const

export const CLASE_NICE: Record<number, string> = {
  1: 'Químicos', 2: 'Pinturas', 3: 'Cosmética', 4: 'Lubricantes',
  5: 'Farmacéutica', 6: 'Metales', 7: 'Maquinaria', 8: 'Herramientas',
  9: 'Electrónica', 10: 'Instrumentos médicos', 11: 'Iluminación',
  12: 'Vehículos', 13: 'Armas', 14: 'Joyería', 15: 'Instrumentos musicales',
  16: 'Papel/Imprenta', 17: 'Caucho', 18: 'Cuero', 19: 'Construcción',
  20: 'Muebles', 21: 'Utensilios del hogar', 22: 'Cuerdas/Textiles',
  23: 'Hilos', 24: 'Tejidos', 25: 'Vestimenta', 26: 'Encajes',
  27: 'Alfombras', 28: 'Juguetes', 29: 'Alimentos procesados',
  30: 'Café/Harina/Pastelería', 31: 'Productos agrícolas', 32: 'Cervezas',
  33: 'Bebidas alcohólicas', 34: 'Tabaco', 35: 'Publicidad/Negocios',
  36: 'Finanzas/Seguros', 37: 'Construcción/Reparación', 38: 'Telecomunicaciones',
  39: 'Transporte', 40: 'Tratamiento de materiales', 41: 'Educación/Entretenimiento',
  42: 'Tecnología/Software', 43: 'Gastronomía', 44: 'Medicina/Veterinaria',
  45: 'Servicios legales/Seguridad',
}
