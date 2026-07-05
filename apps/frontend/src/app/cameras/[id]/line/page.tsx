'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import { cameras } from '@/lib/api'
import { directionLabel } from '@/lib/utils'

type Point = { x: number; y: number }

export default function LineConfigPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [imgSrc, setImgSrc] = useState<string>('')
  const [imgSize, setImgSize] = useState({ w: 640, h: 480 })
  const [points, setPoints] = useState<Point[]>([])
  const [direction, setDirection] = useState<'entry' | 'exit' | 'both'>('both')
  const [activeClasses, setActiveClasses] = useState<string[]>(['car', 'truck', 'bus', 'motorcycle'])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [mode, setMode] = useState<'draw' | 'view'>('view')

  const CLASSES = ['car', 'truck', 'bus', 'motorcycle']
  const CLASS_LABELS: Record<string, string> = { car: 'Carro', truck: 'Caminhão', bus: 'Ônibus', motorcycle: 'Moto' }

  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    if (imgSrc) {
      const img = new Image()
      img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
        if (points.length >= 2) {
          const px1 = points[0].x * canvas.width
          const py1 = points[0].y * canvas.height
          const px2 = points[1].x * canvas.width
          const py2 = points[1].y * canvas.height
          ctx.strokeStyle = '#ef4444'
          ctx.lineWidth = 3
          ctx.beginPath()
          ctx.moveTo(px1, py1)
          ctx.lineTo(px2, py2)
          ctx.stroke()
          ;[{ x: px1, y: py1 }, { x: px2, y: py2 }].forEach(p => {
            ctx.fillStyle = '#ef4444'
            ctx.beginPath()
            ctx.arc(p.x, p.y, 6, 0, 2 * Math.PI)
            ctx.fill()
            ctx.strokeStyle = '#ffffff'
            ctx.lineWidth = 2
            ctx.beginPath()
            ctx.arc(p.x, p.y, 6, 0, 2 * Math.PI)
            ctx.stroke()
          })
        } else if (points.length === 1) {
          const px = points[0].x * canvas.width
          const py = points[0].y * canvas.height
          ctx.fillStyle = '#ef4444'
          ctx.beginPath()
          ctx.arc(px, py, 6, 0, 2 * Math.PI)
          ctx.fill()
          ctx.strokeStyle = '#ffffff'
          ctx.lineWidth = 2
          ctx.beginPath()
          ctx.arc(px, py, 6, 0, 2 * Math.PI)
          ctx.stroke()
        }
      }
      img.src = imgSrc
    } else {
      ctx.fillStyle = '#1f2937'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#6b7280'
      ctx.font = '14px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('Capture um frame para desenhar a linha', canvas.width / 2, canvas.height / 2)
    }
  }, [imgSrc, points])

  useEffect(() => { drawCanvas() }, [drawCanvas])

  async function captureFrame() {
    setLoading(true)
    setError('')
    try {
      const data = await cameras.getFrame(id)
      setImgSrc(`data:image/jpeg;base64,${data.image_base64}`)
      setImgSize({ w: data.width, h: data.height })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao capturar frame')
    } finally {
      setLoading(false)
    }
  }

  async function loadExistingLine() {
    try {
      const line = await cameras.getCountingLine(id)
      if (line) {
        setPoints([
          { x: line.x1_relative, y: line.y1_relative },
          { x: line.x2_relative, y: line.y2_relative },
        ])
        setDirection(line.direction)
        setActiveClasses(line.active_classes)
      }
    } catch {
      // No line configured yet — that's fine
    }
  }

  useEffect(() => {
    captureFrame()
    loadExistingLine()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  function handleCanvasClick(e: React.MouseEvent<HTMLCanvasElement>) {
    if (mode !== 'draw') return
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = (e.clientY - rect.top) / rect.height
    if (points.length === 0 || points.length >= 2) {
      setPoints([{ x, y }])
    } else {
      setPoints(prev => [...prev, { x, y }])
      setMode('view')
    }
  }

  async function saveLine() {
    if (points.length < 2) { setError('Desenhe a linha primeiro clicando no canvas'); return }
    setSaving(true)
    setError('')
    try {
      await cameras.saveCountingLine(id, {
        x1_relative: points[0].x,
        y1_relative: points[0].y,
        x2_relative: points[1].x,
        y2_relative: points[1].y,
        direction,
        active_classes: activeClasses,
      })
      setSuccess('Linha salva com sucesso!')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar linha')
    } finally {
      setSaving(false)
    }
  }

  function toggleClass(cls: string) {
    setActiveClasses(prev =>
      prev.includes(cls) ? prev.filter(c => c !== cls) : [...prev, cls]
    )
  }

  return (
    <AppLayout>
      <div className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => router.push('/cameras')} className="text-gray-400 hover:text-gray-600 text-sm">
            ← Câmeras
          </button>
          <span className="text-gray-300">/</span>
          <h2 className="text-xl font-semibold text-gray-900">Configuração da Linha de Contagem</h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Canvas area */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border p-4">
              <div className="flex gap-2 mb-3 flex-wrap">
                <button
                  onClick={captureFrame}
                  disabled={loading}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 disabled:opacity-50 transition"
                >
                  {loading ? 'Carregando...' : '📷 Capturar Frame'}
                </button>
                <button
                  onClick={() => { setMode('draw'); setPoints([]) }}
                  className={`px-3 py-1.5 rounded text-sm transition ${mode === 'draw' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                >
                  ✏️ Desenhar Nova Linha
                </button>
                <button
                  onClick={() => setPoints([])}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200 transition"
                >
                  🗑️ Limpar Linha
                </button>
              </div>

              {mode === 'draw' && (
                <div className="bg-yellow-50 border border-yellow-200 rounded px-3 py-2 text-sm text-yellow-800 mb-3">
                  {points.length === 0
                    ? '1° Clique para definir o ponto inicial da linha'
                    : '2° Clique para definir o ponto final da linha'}
                </div>
              )}

              <canvas
                ref={canvasRef}
                width={640}
                height={480}
                onClick={handleCanvasClick}
                className={`w-full rounded border bg-gray-900 ${mode === 'draw' ? 'cursor-crosshair' : 'cursor-default'}`}
              />

              {points.length === 2 && (
                <p className="text-xs text-gray-500 mt-2">
                  P1: ({(points[0].x * 100).toFixed(1)}%, {(points[0].y * 100).toFixed(1)}%)
                  {' — '}
                  P2: ({(points[1].x * 100).toFixed(1)}%, {(points[1].y * 100).toFixed(1)}%)
                </p>
              )}
              {imgSize.w > 0 && (
                <p className="text-xs text-gray-400 mt-1">Resolução original: {imgSize.w}×{imgSize.h}px</p>
              )}
            </div>
          </div>

          {/* Controls */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg border p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Sentido da Contagem</h3>
              <div className="space-y-2">
                {(['entry', 'exit', 'both'] as const).map(d => (
                  <label key={d} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="direction"
                      value={d}
                      checked={direction === d}
                      onChange={() => setDirection(d)}
                      className="accent-blue-600"
                    />
                    <span className="text-sm">{directionLabel(d)}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-lg border p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Tipos de Veículos</h3>
              <div className="space-y-2">
                {CLASSES.map(cls => (
                  <label key={cls} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={activeClasses.includes(cls)}
                      onChange={() => toggleClass(cls)}
                      className="accent-blue-600"
                    />
                    <span className="text-sm">{CLASS_LABELS[cls]}</span>
                  </label>
                ))}
              </div>
              {activeClasses.length === 0 && (
                <p className="text-xs text-red-500 mt-2">Selecione pelo menos um tipo de veículo</p>
              )}
            </div>

            <div className="space-y-2">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">{error}</div>
              )}
              {success && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-3 py-2 rounded text-sm">{success}</div>
              )}

              <button
                onClick={saveLine}
                disabled={saving || points.length < 2 || activeClasses.length === 0}
                className="w-full bg-blue-600 text-white py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {saving ? 'Salvando...' : '💾 Salvar Linha'}
              </button>

              <button
                onClick={() => router.push('/cameras')}
                className="w-full bg-gray-100 text-gray-700 py-2 rounded text-sm hover:bg-gray-200 transition"
              >
                Voltar para Câmeras
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
