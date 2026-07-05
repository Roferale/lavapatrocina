'use client'
import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/AppLayout'
import { cameras } from '@/lib/api'

interface FormState {
  name: string
  rtsp_url: string
  username: string
  password: string
  status: 'active' | 'inactive'
  processing_fps: number
  processing_width: number
  processing_height: number
  min_confidence: number
}

export default function EditCameraPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [form, setForm] = useState<FormState>({
    name: '',
    rtsp_url: '',
    username: '',
    password: '',
    status: 'active',
    processing_fps: 10,
    processing_width: 640,
    processing_height: 480,
    min_confidence: 0.5,
  })
  const [loadingData, setLoadingData] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [error, setError] = useState('')
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  useEffect(() => {
    async function fetchCamera() {
      try {
        const data = await cameras.get(id)
        setForm({
          name: data.name,
          rtsp_url: '',
          username: '',
          password: '',
          status: data.status,
          processing_fps: data.processing_fps,
          processing_width: data.processing_width,
          processing_height: data.processing_height,
          min_confidence: data.min_confidence,
        })
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Erro ao carregar câmera')
      } finally {
        setLoadingData(false)
      }
    }
    fetchCamera()
  }, [id])

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value, type } = e.target
    setForm(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) : value,
    }))
  }

  async function handleTest() {
    if (!form.rtsp_url) {
      setTestResult({ success: false, message: 'Informe a URL RTSP para testar' })
      return
    }
    setTesting(true)
    setTestResult(null)
    try {
      const result = await cameras.testConnection({
        rtsp_url: form.rtsp_url,
        username: form.username || undefined,
        password: form.password || undefined,
      })
      setTestResult(result)
    } catch (err: unknown) {
      setTestResult({ success: false, message: err instanceof Error ? err.message : 'Erro ao testar conexão' })
    } finally {
      setTesting(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        status: form.status,
        processing_fps: form.processing_fps,
        processing_width: form.processing_width,
        processing_height: form.processing_height,
        min_confidence: form.min_confidence,
      }
      if (form.rtsp_url) payload.rtsp_url = form.rtsp_url
      if (form.username) payload.username = form.username
      if (form.password) payload.password = form.password
      await cameras.update(id, payload)
      router.push('/cameras')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao atualizar câmera')
    } finally {
      setSaving(false)
    }
  }

  if (loadingData) {
    return (
      <AppLayout>
        <div className="p-6 text-center text-gray-400">Carregando câmera...</div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="p-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => router.push('/cameras')} className="text-gray-400 hover:text-gray-600 text-sm">
            ← Câmeras
          </button>
          <span className="text-gray-300">/</span>
          <h2 className="text-xl font-semibold text-gray-900">Editar Câmera</h2>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">{error}</div>
        )}

        <div className="bg-blue-50 border border-blue-200 rounded-md px-4 py-3 mb-4 text-sm text-blue-700">
          <strong>Nota:</strong> URL RTSP e credenciais foram salvos com segurança. Deixe os campos em branco para manter os valores atuais, ou preencha para atualizar.
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-lg border p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
            <input
              name="name" type="text" required value={form.name} onChange={handleChange}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nova URL RTSP <span className="text-gray-400 font-normal">(opcional — deixe em branco para manter)</span>
            </label>
            <div className="flex gap-2">
              <input
                name="rtsp_url" type="text" value={form.rtsp_url} onChange={handleChange}
                className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="rtsp://... (deixe em branco para manter)"
              />
              <button
                type="button" onClick={handleTest} disabled={testing}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 disabled:opacity-50 whitespace-nowrap"
              >
                {testing ? 'Testando...' : 'Testar'}
              </button>
            </div>
            {testResult && (
              <div className={`mt-2 px-3 py-2 rounded text-sm ${testResult.success ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'}`}>
                {testResult.success ? '✓ ' : '✗ '}{testResult.message}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Novo Usuário <span className="text-gray-400 font-normal">(opcional)</span>
              </label>
              <input
                name="username" type="text" value={form.username} onChange={handleChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Deixe em branco para manter"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nova Senha <span className="text-gray-400 font-normal">(opcional)</span>
              </label>
              <input
                name="password" type="password" value={form.password} onChange={handleChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Deixe em branco para manter"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              name="status" value={form.status} onChange={handleChange}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
            </select>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">FPS</label>
              <input
                name="processing_fps" type="number" min="1" max="30" step="1"
                value={form.processing_fps} onChange={handleChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Largura (px)</label>
              <input
                name="processing_width" type="number" min="320" max="1920" step="1"
                value={form.processing_width} onChange={handleChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Altura (px)</label>
              <input
                name="processing_height" type="number" min="240" max="1080" step="1"
                value={form.processing_height} onChange={handleChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confiança Mínima: <span className="text-blue-600 font-semibold">{Math.round(form.min_confidence * 100)}%</span>
            </label>
            <input
              name="min_confidence" type="range" min="0.1" max="1.0" step="0.05"
              value={form.min_confidence} onChange={handleChange}
              className="w-full accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>10%</span>
              <span>100%</span>
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit" disabled={saving}
              className="flex-1 bg-blue-600 text-white py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {saving ? 'Salvando...' : 'Salvar Alterações'}
            </button>
            <button
              type="button" onClick={() => router.push('/cameras')}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 transition"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  )
}
