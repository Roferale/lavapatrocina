'use client'
import { useState, useEffect, useCallback } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import { users } from '@/lib/api'
import { User, Role } from '@/types'
import { formatDate, roleLabel } from '@/lib/utils'

interface UserForm {
  email: string
  full_name: string
  password: string
  role: Role
  is_active: boolean
}

const emptyForm: UserForm = {
  email: '',
  full_name: '',
  password: '',
  role: 'operator',
  is_active: true,
}

export default function UsersPage() {
  const [userList, setUserList] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [form, setForm] = useState<UserForm>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await users.list()
      setUserList(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar usuários')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function openCreate() {
    setEditingUser(null)
    setForm(emptyForm)
    setFormError('')
    setShowModal(true)
  }

  function openEdit(user: User) {
    setEditingUser(user)
    setForm({
      email: user.email,
      full_name: user.full_name,
      password: '',
      role: user.role,
      is_active: user.is_active,
    })
    setFormError('')
    setShowModal(true)
  }

  function handleFormChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value, type } = e.target
    const checked = (e.target as HTMLInputElement).checked
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      if (editingUser) {
        const payload: Partial<UserForm> = {
          email: form.email,
          full_name: form.full_name,
          role: form.role,
          is_active: form.is_active,
        }
        if (form.password) payload.password = form.password
        await users.update(editingUser.id, payload)
      } else {
        if (!form.password) { setFormError('Senha é obrigatória para novos usuários'); setSaving(false); return }
        await users.create(form)
      }
      setShowModal(false)
      load()
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Erro ao salvar usuário')
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleActive(user: User) {
    try {
      await users.update(user.id, { is_active: !user.is_active })
      setUserList(prev => prev.map(u => u.id === user.id ? { ...u, is_active: !user.is_active } : u))
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Erro ao atualizar usuário')
    }
  }

  return (
    <AppLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Usuários</h2>
          <button
            onClick={openCreate}
            className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition"
          >
            + Novo Usuário
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">{error}</div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400">Carregando usuários...</div>
        ) : (
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {['Nome', 'E-mail', 'Perfil', 'Status', 'Criado em', 'Ações'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {userList.map(user => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{user.full_name}</td>
                    <td className="px-4 py-3 text-gray-600">{user.email}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        user.role === 'admin' ? 'bg-purple-100 text-purple-700'
                        : user.role === 'operator' ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600'
                      }`}>
                        {roleLabel(user.role)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${user.is_active ? 'bg-green-500' : 'bg-red-400'}`} />
                        {user.is_active ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{formatDate(user.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => openEdit(user)}
                          className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => handleToggleActive(user)}
                          className={`text-xs font-medium ${user.is_active ? 'text-orange-500 hover:text-orange-700' : 'text-green-600 hover:text-green-800'}`}
                        >
                          {user.is_active ? 'Desativar' : 'Ativar'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {userList.length === 0 && (
              <div className="text-center py-10 text-gray-400">Nenhum usuário encontrado</div>
            )}
          </div>
        )}

        {/* Modal */}
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
              <div className="px-6 py-4 border-b flex items-center justify-between">
                <h3 className="text-base font-semibold text-gray-900">
                  {editingUser ? 'Editar Usuário' : 'Novo Usuário'}
                </h3>
                <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
              </div>
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                {formError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">{formError}</div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome Completo *</label>
                  <input
                    name="full_name" type="text" required value={form.full_name} onChange={handleFormChange}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="João Silva"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">E-mail *</label>
                  <input
                    name="email" type="email" required value={form.email} onChange={handleFormChange}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="joao@empresa.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Senha {editingUser ? <span className="text-gray-400 font-normal">(deixe em branco para manter)</span> : '*'}
                  </label>
                  <input
                    name="password" type="password" value={form.password} onChange={handleFormChange}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Perfil</label>
                  <select
                    name="role" value={form.role} onChange={handleFormChange}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="admin">Administrador</option>
                    <option value="operator">Operador</option>
                    <option value="readonly">Somente Leitura</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox" id="is_active" name="is_active"
                    checked={form.is_active} onChange={handleFormChange}
                    className="accent-blue-600"
                  />
                  <label htmlFor="is_active" className="text-sm text-gray-700">Usuário ativo</label>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    type="submit" disabled={saving}
                    className="flex-1 bg-blue-600 text-white py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
                  >
                    {saving ? 'Salvando...' : editingUser ? 'Salvar Alterações' : 'Criar Usuário'}
                  </button>
                  <button
                    type="button" onClick={() => setShowModal(false)}
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 transition"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
