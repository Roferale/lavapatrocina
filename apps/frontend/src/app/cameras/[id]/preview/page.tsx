'use client'
import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import { cameras } from '@/lib/api'

export default function CameraPreviewPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [imgSrc, setImgSrc] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchFrame = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await cameras.getFrame(id)
      setImgSrc(`data:image/jpeg;base64,${data.image_base64}`)
      setDims({ w: data.width, h: data.height })
      setLastUpdated(new Date())
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao capturar frame')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchFrame()
  }, [fetchFrame])

  return (
    <AppLayout>
      <div className="p-6 max-w-4xl">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => router.push('/cameras')} className="text-gray-400 hover:text-gray-600 text-sm">
            ← Câmeras
          </button>
          <span className="text-gray-300">/</span>
          <h2 className="text-xl font-semibold text-gray-900">Preview da Câmera</h2>
        </div>

        <div className="bg-white rounded-lg border p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-gray-500">
              {dims && <span>Resolução: {dims.w}×{dims.h}px</span>}
              {lastUpdated && (
                <span className="ml-4">
                  Atualizado às {lastUpdated.toLocaleTimeString('pt-BR')}
                </span>
              )}
            </div>
            <button
              onClick={fetchFrame}
              disabled={loading}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {loading ? 'Carregando...' : '🔄 Atualizar Frame'}
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
              {error}
              <p className="mt-1 text-xs text-red-500">
                Verifique se a câmera está online e se as configurações RTSP estão corretas.
              </p>
            </div>
          )}

          <div className="bg-gray-900 rounded-lg overflow-hidden flex items-center justify-center" style={{ minHeight: 360 }}>
            {loading && !imgSrc ? (
              <div className="text-gray-400 text-sm">Carregando frame...</div>
            ) : imgSrc ? (
              <img
                src={imgSrc}
                alt="Frame da câmera"
                className="w-full h-auto rounded-lg"
                style={{ maxHeight: 600 }}
              />
            ) : !error ? (
              <div className="text-gray-500 text-sm">Nenhum frame disponível</div>
            ) : null}
          </div>

          {imgSrc && !error && (
            <p className="text-xs text-gray-400 mt-3 text-center">
              Este é um frame estático. Clique em &quot;Atualizar Frame&quot; para obter a imagem mais recente.
            </p>
          )}
        </div>

        <div className="mt-4 flex gap-3">
          <button
            onClick={() => router.push(`/cameras/${id}/line`)}
            className="bg-blue-50 text-blue-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-100 transition"
          >
            Configurar Linha de Contagem
          </button>
          <button
            onClick={() => router.push(`/cameras/${id}/edit`)}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-md text-sm hover:bg-gray-200 transition"
          >
            Editar Câmera
          </button>
        </div>
      </div>
    </AppLayout>
  )
}
