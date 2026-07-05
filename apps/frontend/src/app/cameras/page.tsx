'use client'
import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import AppLayout from '@/components/layout/AppLayout'
import { cameras } from '@/lib/api'
import { Camera } from '@/types'
import { formatDate, statusLabel } from '@/lib/utils'

export default function CamerasPage() {
  const [cameraList, setCameraList] = useState<Camera[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await cameras.list()
      setCameraList(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar câmeras')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Tem certeza que deseja excluir a câmera "${name}"?`)) return
    setDeleting(id)
    try {
      await cameras.delete(id)
      setCameraList(prev => prev.filter(c => c.id !== id))
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Erro ao excluir câmera')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <AppLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Câmeras</h2>
          <Link
            href="/cameras/new"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition"
          >
            + Nova Câmera
          </Link>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">{error}</div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400">Carregando câmeras...</div>
        ) : cameraList.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border">
            <p className="text-gray-500 mb-2">Nenhuma câmera cadastrada.</p>
            <Link href="/cameras/new" className="text-blue-600 text-sm hover:underline">
              Adicionar primeira câmera
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {cameraList.map(camera => (
              <div key={camera.id} className="bg-white rounded-lg border p-5 flex flex-col gap-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-semibold text-gray-900 truncate">{camera.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                        camera.is_online
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${camera.is_online ? 'bg-green-500' : 'bg-gray-400'}`} />
                        {camera.is_online ? 'Online' : 'Offline'}
                      </span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        camera.status === 'active'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {statusLabel(camera.status)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-xs text-gray-500 space-y-1">
                  <div className="flex justify-between">
                    <span>FPS:</span>
                    <span className="font-medium text-gray-700">{camera.processing_fps}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Resolução:</span>
                    <span className="font-medium text-gray-700">{camera.processing_width}×{camera.processing_height}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Confiança mín.:</span>
                    <span className="font-medium text-gray-700">{Math.round(camera.min_confidence * 100)}%</span>
                  </div>
                  {camera.last_seen_at && (
                    <div className="flex justify-between">
                      <span>Visto por último:</span>
                      <span className="font-medium text-gray-700">{formatDate(camera.last_seen_at)}</span>
                    </div>
                  )}
                </div>

                <div className="flex gap-2 pt-1 flex-wrap">
                  <Link
                    href={`/cameras/${camera.id}/edit`}
                    className="flex-1 text-center bg-gray-100 text-gray-700 px-3 py-1.5 rounded text-xs font-medium hover:bg-gray-200 transition"
                  >
                    Editar
                  </Link>
                  <Link
                    href={`/cameras/${camera.id}/line`}
                    className="flex-1 text-center bg-blue-50 text-blue-700 px-3 py-1.5 rounded text-xs font-medium hover:bg-blue-100 transition"
                  >
                    Linha
                  </Link>
                  <Link
                    href={`/cameras/${camera.id}/preview`}
                    className="flex-1 text-center bg-green-50 text-green-700 px-3 py-1.5 rounded text-xs font-medium hover:bg-green-100 transition"
                  >
                    Preview
                  </Link>
                  <button
                    onClick={() => handleDelete(camera.id, camera.name)}
                    disabled={deleting === camera.id}
                    className="flex-1 text-center bg-red-50 text-red-600 px-3 py-1.5 rounded text-xs font-medium hover:bg-red-100 transition disabled:opacity-50"
                  >
                    {deleting === camera.id ? '...' : 'Excluir'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
