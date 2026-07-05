'use client'
import { useState, useEffect, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import { system } from '@/lib/api'
import { SystemLog } from '@/types'
import { formatDate } from '@/lib/utils'

const PAGE_SIZE = 50

const LEVELS = ['', 'error', 'warning', 'info', 'debug']

const levelConfig: Record<string, { label: string; bg: string; text: string }> = {
  error:   { label: 'Erro',    bg: 'bg-red-100',    text: 'text-red-700'   },
  warning: { label: 'Aviso',   bg: 'bg-yellow-100', text: 'text-yellow-700'},
  info:    { label: 'Info',    bg: 'bg-blue-100',   text: 'text-blue-700'  },
  debug:   { label: 'Debug',   bg: 'bg-gray-100',   text: 'text-gray-600'  },
}

function LevelBadge({ level }: { level: string }) {
  const cfg = levelConfig[level] ?? { label: level, bg: 'bg-gray-100', text: 'text-gray-600' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  )
}

export default function LogsPage() {
  const [logs, setLogs] = useState<SystemLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [levelFilter, setLevelFilter] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const load = useCallback(async (pg: number, lvl: string) => {
    setLoading(true)
    setError('')
    try {
      const params: Record<string, string | number | undefined> = {
        page: pg,
        page_size: PAGE_SIZE,
      }
      if (lvl) params.level = lvl
      const res = await system.getLogs(params)
      setLogs(res.items)
      setTotal(res.total)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar logs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(page, levelFilter)
  }, [page, levelFilter, load])

  function handleLevelChange(lvl: string) {
    setLevelFilter(lvl)
    setPage(1)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <AppLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Logs do Sistema</h2>
          <button
            onClick={() => load(page, levelFilter)}
            className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 transition"
          >
            🔄 Atualizar
          </button>
        </div>

        {/* Level filter */}
        <div className="flex gap-2 mb-4">
          {LEVELS.map(lvl => (
            <button
              key={lvl || 'all'}
              onClick={() => handleLevelChange(lvl)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                levelFilter === lvl
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {lvl ? (levelConfig[lvl]?.label ?? lvl) : 'Todos'}
            </button>
          ))}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">{error}</div>
        )}

        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b text-sm text-gray-500">
            {total} registro{total !== 1 ? 's' : ''} encontrado{total !== 1 ? 's' : ''}
          </div>

          {loading ? (
            <div className="text-center py-10 text-gray-400">Carregando logs...</div>
          ) : logs.length === 0 ? (
            <div className="text-center py-10 text-gray-400">Nenhum log encontrado</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['Nível', 'Fonte', 'Mensagem', 'Data/Hora', 'Detalhes'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {logs.map(log => (
                    <>
                      <tr
                        key={log.id}
                        className={`hover:bg-gray-50 ${log.level === 'error' ? 'bg-red-50/30' : ''}`}
                      >
                        <td className="px-4 py-3 whitespace-nowrap">
                          <LevelBadge level={log.level} />
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          <code className="text-xs">{log.source}</code>
                        </td>
                        <td className="px-4 py-3 text-gray-800 max-w-md">
                          <p className="truncate">{log.message}</p>
                        </td>
                        <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">{formatDate(log.created_at)}</td>
                        <td className="px-4 py-3">
                          {log.details && Object.keys(log.details).length > 0 ? (
                            <button
                              onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                              className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                            >
                              {expanded === log.id ? 'Ocultar' : 'Ver'}
                            </button>
                          ) : (
                            <span className="text-gray-300 text-xs">—</span>
                          )}
                        </td>
                      </tr>
                      {expanded === log.id && log.details && (
                        <tr key={`${log.id}-details`} className="bg-gray-50">
                          <td colSpan={5} className="px-4 py-3">
                            <pre className="text-xs text-gray-700 bg-gray-100 rounded p-3 overflow-x-auto max-h-40">
                              {JSON.stringify(log.details, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t flex items-center justify-between">
              <span className="text-sm text-gray-500">Página {page} de {totalPages}</span>
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
