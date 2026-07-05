import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'dd/MM/yyyy HH:mm', { locale: ptBR })
  } catch {
    return dateStr
  }
}

export function formatDateOnly(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'dd/MM/yyyy', { locale: ptBR })
  } catch {
    return dateStr
  }
}

export function formatConfidence(val: number): string {
  return `${Math.round(val * 100)}%`
}

export function vehicleTypeLabel(type: string): string {
  const map: Record<string, string> = {
    car: 'Carro',
    truck: 'Caminhão',
    bus: 'Ônibus',
    motorcycle: 'Moto',
  }
  return map[type] ?? type
}

export function directionLabel(dir: string): string {
  const map: Record<string, string> = {
    entry: 'Entrada',
    exit: 'Saída',
    both: 'Ambos',
  }
  return map[dir] ?? dir
}

export function statusLabel(s: string): string {
  const map: Record<string, string> = {
    automatic: 'Automático',
    corrected: 'Corrigido',
    removed: 'Removido',
    active: 'Ativo',
    inactive: 'Inativo',
  }
  return map[s] ?? s
}

export function roleLabel(r: string): string {
  const map: Record<string, string> = {
    admin: 'Administrador',
    operator: 'Operador',
    readonly: 'Somente Leitura',
  }
  return map[r] ?? r
}
