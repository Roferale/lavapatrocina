'use client'
import { useState, useEffect, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import { events, cameras } from '@/lib/api'
import { VehicleEvent, Camera, EventFilter } from '@/types'
import { formatDate, vehicleTypeLabel, directionLabel, statusLabel } from '@/lib/utils'

const PAGE_SIZE = 20

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function EventsPage() {
  const [eventList, setEventList] = useState<VehicleEvent[]>([])
  const [cameraList, setCameraList] = useState<Camera[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [exporting, setExporting] = useState<'csv' | 'excel' | null>(null)

  const [filters, setFilters] = useState<EventFilter>({
    date_from: '',
    date_to: '',
    camera_id: '',
    vehicle_type: '',
    direction: undefined,
    status: undefined,
    page: 1,
    page_size: PAGE_SIZE,
  })

  useEffect(() => {
    cameras.list().then(setCameraList).catch(() => {})
  }, [])

  const load = useCallback(async (f: EventFilter) => {
    setLoading(true)
    setError('')
    try {
      const res = await events.list({ ...f, page, page_size: PAGE_SIZE })
      setEventList(res.items)
      setTotal(res.total)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar eventos')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    load(filters)
  }, [page]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleFilterChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = e.target
    setFilters(prev => ({ ...prev, [name]: value || undefined }))
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    load(filters)
  }

  function handleReset() {
    const blank: EventFilter = { page: 1, page_size: PAGE_SIZE }
    setFilters({ date_from: '', date_to: '', camera_id: '', vehicle_type: '', direction: undefined, status: undefined, page: 1, page_size: PAGE_SIZE })
    setPage(1)
    load(blank)
  }

  async function handleDelete(id: string) {
    if (!confirm('Remover este evento?')) return
    setDeleting(id)
    try {
      await events.delete(id)
      setEventList(prev => prev.filter(e => e.id !== id))
      setTotal(prev => prev - 1)
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Erro ao remover evento')
    } finally {
      setDeleting(null)
    }
  }

  async function handleExportCSV() {
    setExporting('csv')
    try {
      const blob = await events.exportCSV(filters)
      downloadBlob(blob, 'eventos.csv')
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Erro ao exportar CSV')
    } finally {
      setExporting(null)
    }
  }

  async function handleExportExcel() {
    setExporting('excel')
    try {
      const blob = await events.exportExcel(filters)
      downloadBlob(blob, 'eventos.xlsx')
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Erro ao exportar Excel')
    } finally {
      setExporting(null)
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <AppLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Histórico de Eventos</h2>
          <div className="flex gap-2">
            <button
              onClick={handleExportCSV}
              disabled={!!exporting}
              className="px-3 py-1.5 bg-green-50 text-green-700 border border-green-200 rounded text-sm hover:bg-green-100 disabled:opacity-50 transition"
            >
              {exporting === 'csv' ? 'Exportando...' : '↓ CSV'}
            </button>
            <button
              onClick={handleExportExcel}
              disabled={!!exporting}
              className="px-3 py-1.5 bg-blue-50 text-blue-700 border border-blue-200 rounded text-sm hover:bg-blue-100 disabled:opacity-50 transition"
            >
              {exporting === 'excel' ? 'Exportando...' : '↓ Excel'}
            </button>
          </div>
        </div>

        {/* Filters */}
        <form onSubmit={handleSearch} className="bg-white rounded-lg border p-4 mb-4">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">De</label>
              <input
                type="date" name="date_from"
                value={filters.date_from || ''}
                onChange={handleFilterChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Até</label>
              <input
                type="date" name="date_to"
                value={filters.date_to || ''}
                onChange={handleFilterChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Câmera</label>
              <select
                name="camera_id"
                value={filters.camera_id || ''}
                onChange={handleFilterChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Todas</option>
                {cameraList.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Tipo de Veículo</label>
              <select
                name="vehicle_type"
                value={filters.vehicle_type || ''}
                onChange={handleFilterChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="car">Carro</option>
                <option value="truck">Caminhão</option>
                <option value="bus">Ônibus</option>
                <option value="motorcycle">Moto</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Sentido</label>
              <select
                name="direction"
                value={filters.direction || ''}
                onChange={handleFilterChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Ambos</option>
                <option value="entry">Entrada</option>
                <option value="exit">Saída</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
              <select
                name="status"
                value={filters.status || ''}
                onChange={handleFilterChange}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="automatic">Automático</option>
                <option value="corrected">Corrigido</option>
                <option value="removed">Removido</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button
              type="submit"
              className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 transition"
            >
              Filtrar
            </button>
            <button
              type="button" onClick={handleReset}
              className="bg-gray-100 text-gray-600 px-4 py-1.5 rounded text-sm hover:bg-gray-200 transition"
            >
              Limpar
            </button>
          </div>
        </form>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">{error}</div>
        )}

        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <span className="text-sm text-gray-500">
              {total} evento{total !== 1 ? 's' : ''} encontrado{total !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="overflow-x-auto">
            {loading ? (
              <div className="text-center py-10 text-gray-400">Carregando eventos...</div>
            ) : eventList.length === 0 ? (
              <div className="text-center py-10 text-gray-400">Nenhum evento encontrado para os filtros selecionados</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['Data/Hora', 'Câmera', 'Tipo', 'Sentido', 'Confiança', 'Status', 'Ação'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {eventList.map(ev => (
                    <tr key={ev.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{formatDate(ev.event_time)}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {cameraList.find(c => c.id === ev.camera_id)?.name || ev.camera_id.slice(0, 8) + '...'}
                      </td>
                      <td className="px-4 py-3">{vehicleTypeLabel(ev.vehicle_type)}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ev.direction === 'entry' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                          {directionLabel(ev.direction)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{Math.round(ev.confidence * 100)}%</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          ev.status === 'automatic' ? 'bg-blue-100 text-blue-700'
                          : ev.status === 'corrected' ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-500'
                        }`}>
                          {statusLabel(ev.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleDelete(ev.id)}
                          disabled={deleting === ev.id}
                          className="text-red-500 hover:text-red-700 text-xs disabled:opacity-50"
                        >
                          {deleting === ev.id ? '...' : 'Remover'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t flex items-center justify-between">
              <span className="text-sm text-gray-500">
                Página {page} de {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 bg-gray-100 text-gray-600 rounded text-sm disabled:opacity-40 hover:bg-gray-200"
                >
                  ← Anterior
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 bg-gray-100 text-gray-600 rounded text-sm disabled:opacity-40 hover:bg-gray-200"
                >
                  Próxima →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
