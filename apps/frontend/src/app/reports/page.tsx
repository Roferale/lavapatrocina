'use client'
import { useState, useEffect, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import { events, cameras } from '@/lib/api'
import { Camera, VehicleEvent } from '@/types'
import { formatDate, vehicleTypeLabel, directionLabel } from '@/lib/utils'

type Period = 'today' | 'week' | 'month' | 'custom'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function toLocalISO(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function getPeriodDates(period: Period): { from: string; to: string } {
  const today = new Date()
  const to = toLocalISO(today)
  if (period === 'today') return { from: to, to }
  if (period === 'week') {
    const from = new Date(today)
    from.setDate(today.getDate() - 6)
    return { from: toLocalISO(from), to }
  }
  if (period === 'month') {
    const from = new Date(today.getFullYear(), today.getMonth(), 1)
    return { from: toLocalISO(from), to }
  }
  return { from: '', to: '' }
}

export default function ReportsPage() {
  const [period, setPeriod] = useState<Period>('today')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [cameraId, setCameraId] = useState('')
  const [cameraList, setCameraList] = useState<Camera[]>([])
  const [eventList, setEventList] = useState<VehicleEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    cameras.list().then(setCameraList).catch(() => {})
  }, [])

  const buildFilter = useCallback(() => {
    const { from, to } = period === 'custom'
      ? { from: customFrom, to: customTo }
      : getPeriodDates(period)
    return {
      date_from: from || undefined,
      date_to: to || undefined,
      camera_id: cameraId || undefined,
      page: 1,
      page_size: 500,
    }
  }, [period, customFrom, customTo, cameraId])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const f = buildFilter()
      const res = await events.list(f)
      setEventList(res.items)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar relatório')
    } finally {
      setLoading(false)
    }
  }, [buildFilter])

  useEffect(() => { load() }, [period, cameraId]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleExportCSV() {
    setExporting(true)
    try {
      const blob = await events.exportCSV(buildFilter())
      downloadBlob(blob, 'relatorio.csv')
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Erro ao exportar')
    } finally {
      setExporting(false)
    }
  }

  // Aggregations
  const totalCount = eventList.length
  const entries = eventList.filter(e => e.direction === 'entry').length
  const exits = eventList.filter(e => e.direction === 'exit').length

  const byType: Record<string, number> = {}
  eventList.forEach(e => { byType[e.vehicle_type] = (byType[e.vehicle_type] || 0) + 1 })

  const byDay: Record<string, number> = {}
  eventList.forEach(e => {
    const day = e.event_time.slice(0, 10)
    byDay[day] = (byDay[day] || 0) + 1
  })
  const dailyData = Object.entries(byDay).sort(([a], [b]) => a.localeCompare(b))

  const maxDay = Math.max(...dailyData.map(([, c]) => c), 1)

  const periodLabels: Record<Period, string> = {
    today: 'Hoje',
    week: 'Esta Semana',
    month: 'Este Mês',
    custom: 'Personalizado',
  }

  return (
    <AppLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Relatórios</h2>
          <button
            onClick={handleExportCSV}
            disabled={exporting || loading || totalCount === 0}
            className="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition"
          >
            {exporting ? 'Exportando...' : '↓ Exportar CSV'}
          </button>
        </div>

        {/* Period & filters */}
        <div className="bg-white rounded-lg border p-4 mb-6">
          <div className="flex items-center gap-2 mb-4">
            {(['today', 'week', 'month', 'custom'] as Period[]).map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
                  period === p
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {periodLabels[p]}
              </button>
            ))}
          </div>

          {period === 'custom' && (
            <div className="flex items-center gap-3 mb-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Data Inicial</label>
                <input
                  type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Data Final</label>
                <input
                  type="date" value={customTo} onChange={e => setCustomTo(e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={load}
                className="mt-5 px-4 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition"
              >
                Buscar
              </button>
            </div>
          )}

          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600">Câmera:</label>
            <select
              value={cameraId} onChange={e => setCameraId(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Todas</option>
              {cameraList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">{error}</div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400">Carregando relatório...</div>
        ) : (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg border p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{totalCount}</p>
              </div>
              <div className="bg-white rounded-lg border p-5 border-l-4 border-l-green-400">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Entradas</p>
                <p className="text-3xl font-bold text-green-700 mt-1">{entries}</p>
              </div>
              <div className="bg-white rounded-lg border p-5 border-l-4 border-l-orange-400">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Saídas</p>
                <p className="text-3xl font-bold text-orange-700 mt-1">{exits}</p>
              </div>
              <div className="bg-white rounded-lg border p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Saldo</p>
                <p className={`text-3xl font-bold mt-1 ${entries - exits >= 0 ? 'text-blue-700' : 'text-red-600'}`}>
                  {entries - exits >= 0 ? '+' : ''}{entries - exits}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* By type */}
              <div className="bg-white rounded-lg border p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Por Tipo de Veículo</h3>
                {Object.keys(byType).length === 0 ? (
                  <p className="text-gray-400 text-sm">Sem dados</p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(byType).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                      <div key={type}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-700">{vehicleTypeLabel(type)}</span>
                          <span className="font-semibold text-gray-900">{count}</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${(count / totalCount) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* By direction */}
              <div className="bg-white rounded-lg border p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Por Sentido</h3>
                {totalCount === 0 ? (
                  <p className="text-gray-400 text-sm">Sem dados</p>
                ) : (
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-700">{directionLabel('entry')}</span>
                        <span className="font-semibold text-gray-900">{entries}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className="bg-green-500 h-2 rounded-full" style={{ width: `${(entries / totalCount) * 100}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-700">{directionLabel('exit')}</span>
                        <span className="font-semibold text-gray-900">{exits}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className="bg-orange-400 h-2 rounded-full" style={{ width: `${(exits / totalCount) * 100}%` }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Daily chart */}
            {dailyData.length > 1 && (
              <div className="bg-white rounded-lg border p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Evolução Diária</h3>
                <svg width="100%" viewBox={`0 0 600 130`}>
                  {dailyData.map(([date, count], i) => {
                    const barW = 580 / dailyData.length - 4
                    const x = i * (barW + 4) + 10
                    const barH = (count / maxDay) * 100
                    const label = date.slice(5)
                    return (
                      <g key={date}>
                        <rect x={x} y={100 - barH} width={barW} height={barH} fill="#3b82f6" rx="2" />
                        <text x={x + barW / 2} y={118} textAnchor="middle" fontSize="9" fill="#9ca3af">{label}</text>
                        {count > 0 && (
                          <text x={x + barW / 2} y={100 - barH - 4} textAnchor="middle" fontSize="9" fill="#374151">{count}</text>
                        )}
                      </g>
                    )
                  })}
                </svg>
              </div>
            )}

            {/* Events table */}
            {eventList.length > 0 && (
              <div className="bg-white rounded-lg border">
                <div className="px-5 py-3 border-b">
                  <h3 className="text-sm font-semibold text-gray-700">Eventos do Período</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        {['Data/Hora', 'Tipo', 'Sentido', 'Confiança'].map(h => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {eventList.slice(0, 100).map(ev => (
                        <tr key={ev.id} className="hover:bg-gray-50">
                          <td className="px-4 py-2 text-gray-700">{formatDate(ev.event_time)}</td>
                          <td className="px-4 py-2">{vehicleTypeLabel(ev.vehicle_type)}</td>
                          <td className="px-4 py-2">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ev.direction === 'entry' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                              {directionLabel(ev.direction)}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-gray-500">{Math.round(ev.confidence * 100)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {eventList.length > 100 && (
                    <div className="px-4 py-2 text-xs text-gray-400 text-center">
                      Exibindo 100 de {eventList.length} eventos. Exporte o CSV para ver todos.
                    </div>
                  )}
                </div>
              </div>
            )}

            {totalCount === 0 && (
              <div className="text-center py-12 bg-white rounded-lg border text-gray-400">
                Nenhum evento encontrado no período selecionado.
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
