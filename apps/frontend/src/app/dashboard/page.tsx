'use client'
import { useState, useEffect, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import { dashboard } from '@/lib/api'
import { DashboardMetrics } from '@/types'
import { formatDate, vehicleTypeLabel, directionLabel } from '@/lib/utils'

function MetricCard({ title, value, subtitle, color }: { title: string; value: string | number; subtitle?: string; color?: string }) {
  return (
    <div className={`bg-white rounded-lg border p-6 ${color || ''}`}>
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  )
}

function HourlyChart({ data }: { data: { hour: number; count: number }[] }) {
  const max = Math.max(...data.map(d => d.count), 1)
  const w = 560; const h = 120; const barW = w / 24 - 2
  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-sm font-medium text-gray-700 mb-4">Contagens por Hora (Hoje)</h3>
      <svg width="100%" viewBox={`0 0 ${w} ${h + 20}`}>
        {data.map((d, i) => {
          const barH = (d.count / max) * h
          const x = i * (barW + 2)
          return (
            <g key={i}>
              <rect x={x} y={h - barH} width={barW} height={barH} fill="#3b82f6" rx="2" />
              {i % 4 === 0 && (
                <text x={x + barW / 2} y={h + 15} textAnchor="middle" fontSize="9" fill="#9ca3af">{d.hour}h</text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function DailyChart({ data }: { data: { date: string; count: number }[] }) {
  if (!data || data.length === 0) return null
  const max = Math.max(...data.map(d => d.count), 1)
  const w = 560; const h = 120; const barW = w / data.length - 4
  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-sm font-medium text-gray-700 mb-4">Últimos 7 Dias</h3>
      <svg width="100%" viewBox={`0 0 ${w} ${h + 24}`}>
        {data.map((d, i) => {
          const barH = (d.count / max) * h
          const x = i * (barW + 4)
          const label = d.date.slice(5)
          return (
            <g key={i}>
              <rect x={x} y={h - barH} width={barW} height={barH} fill="#10b981" rx="2" />
              <text x={x + barW / 2} y={h + 15} textAnchor="middle" fontSize="9" fill="#9ca3af">{label}</text>
              {d.count > 0 && (
                <text x={x + barW / 2} y={h - barH - 4} textAnchor="middle" fontSize="9" fill="#374151">{d.count}</text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await dashboard.getMetrics()
      setMetrics(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar dashboard')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [load])

  const hourlyFull = Array.from({ length: 24 }, (_, h) => ({
    hour: h,
    count: metrics?.hourly_counts?.find(d => d.hour === h)?.count || 0,
  }))

  return (
    <AppLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Dashboard</h2>
          <div className="flex items-center gap-3 text-sm">
            <span className={`flex items-center gap-1.5 ${metrics?.camera_online ? 'text-green-600' : 'text-red-500'}`}>
              <span className={`w-2 h-2 rounded-full ${metrics?.camera_online ? 'bg-green-500' : 'bg-red-500'}`} />
              Câmera {metrics?.camera_online ? 'Online' : 'Offline'}
            </span>
            <span className={`flex items-center gap-1.5 ${metrics?.worker_running ? 'text-green-600' : 'text-red-500'}`}>
              <span className={`w-2 h-2 rounded-full ${metrics?.worker_running ? 'bg-green-500' : 'bg-red-500'}`} />
              Worker {metrics?.worker_running ? 'Ativo' : 'Parado'}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Carregando...</div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">{error}</div>
        ) : metrics ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard title="Hoje" value={metrics.today_count} subtitle="veículos detectados" />
              <MetricCard title="Esta Semana" value={metrics.week_count} />
              <MetricCard title="Este Mês" value={metrics.month_count} />
              <MetricCard
                title="Status"
                value={metrics.worker_running ? 'Ativo' : 'Parado'}
                subtitle="worker de processamento"
                color={metrics.worker_running ? 'border-green-200' : 'border-red-200'}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <HourlyChart data={hourlyFull} />
              <DailyChart data={metrics.daily_counts} />
            </div>

            <div className="bg-white rounded-lg border">
              <div className="px-6 py-4 border-b">
                <h3 className="text-sm font-medium text-gray-700">Últimos Veículos Detectados</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Data/Hora', 'Tipo', 'Sentido', 'Confiança', 'Status'].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {metrics.recent_events.map(ev => (
                      <tr key={ev.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-700">{formatDate(ev.event_time)}</td>
                        <td className="px-4 py-3">{vehicleTypeLabel(ev.vehicle_type)}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ev.direction === 'entry' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                            {directionLabel(ev.direction)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-500">{Math.round(ev.confidence * 100)}%</td>
                        <td className="px-4 py-3 text-gray-500 capitalize">{ev.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {metrics.recent_events.length === 0 && (
                  <div className="text-center py-8 text-gray-400">Nenhum evento registrado</div>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </AppLayout>
  )
}
