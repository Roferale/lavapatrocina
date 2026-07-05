'use client'
import { useState, useEffect, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import { system } from '@/lib/api'
import { AppSetting } from '@/types'
import { formatDate } from '@/lib/utils'

export default function SettingsPage() {
  const [settingsList, setSettingsList] = useState<AppSetting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saveSuccess, setSaveSuccess] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await system.getSettings()
      setSettingsList(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar configurações')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function startEdit(setting: AppSetting) {
    setEditingKey(setting.key)
    setEditValue(
      typeof setting.value === 'object'
        ? JSON.stringify(setting.value, null, 2)
        : String(setting.value ?? '')
    )
    setSaveError('')
    setSaveSuccess('')
  }

  function cancelEdit() {
    setEditingKey(null)
    setEditValue('')
    setSaveError('')
  }

  async function handleSave(key: string) {
    setSaving(true)
    setSaveError('')
    setSaveSuccess('')
    try {
      let parsed: unknown = editValue
      // Try to parse numbers and booleans
      if (editValue === 'true') parsed = true
      else if (editValue === 'false') parsed = false
      else if (!isNaN(Number(editValue)) && editValue.trim() !== '') parsed = Number(editValue)
      else {
        try { parsed = JSON.parse(editValue) } catch { /* keep as string */ }
      }
      const updated = await system.updateSetting(key, { value: parsed })
      setSettingsList(prev => prev.map(s => s.key === key ? updated : s))
      setEditingKey(null)
      setSaveSuccess(`Configuração "${key}" salva com sucesso.`)
      setTimeout(() => setSaveSuccess(''), 3000)
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : 'Erro ao salvar configuração')
    } finally {
      setSaving(false)
    }
  }

  function formatValue(val: unknown): string {
    if (val === null || val === undefined) return '—'
    if (typeof val === 'boolean') return val ? 'Verdadeiro' : 'Falso'
    if (typeof val === 'object') return JSON.stringify(val)
    return String(val)
  }

  return (
    <AppLayout>
      <div className="p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Configurações do Sistema</h2>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">{error}</div>
        )}
        {saveSuccess && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4 text-sm">{saveSuccess}</div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400">Carregando configurações...</div>
        ) : settingsList.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border text-gray-400">
            Nenhuma configuração disponível.
          </div>
        ) : (
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {['Chave', 'Descrição', 'Valor Atual', 'Atualizado em', 'Ação'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {settingsList.map(setting => (
                  <tr key={setting.key} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <code className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">{setting.key}</code>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs max-w-xs">{setting.description || '—'}</td>
                    <td className="px-4 py-3">
                      {editingKey === setting.key ? (
                        <div className="space-y-1">
                          <textarea
                            value={editValue}
                            onChange={e => setEditValue(e.target.value)}
                            rows={3}
                            className="w-full border border-gray-300 rounded px-2 py-1 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[200px]"
                          />
                          {saveError && <p className="text-xs text-red-500">{saveError}</p>}
                        </div>
                      ) : (
                        <span className="font-mono text-xs text-gray-700">{formatValue(setting.value)}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{formatDate(setting.updated_at)}</td>
                    <td className="px-4 py-3">
                      {editingKey === setting.key ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSave(setting.key)}
                            disabled={saving}
                            className="bg-blue-600 text-white px-3 py-1 rounded text-xs hover:bg-blue-700 disabled:opacity-50 transition"
                          >
                            {saving ? '...' : 'Salvar'}
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="bg-gray-100 text-gray-600 px-3 py-1 rounded text-xs hover:bg-gray-200 transition"
                          >
                            Cancelar
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEdit(setting)}
                          className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                        >
                          Editar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
