const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  let url = `${BASE_URL}${path}`
  if (params) {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.append(k, String(v))
    })
    const qs = q.toString()
    if (qs) url += `?${qs}`
  }

  const token = typeof window !== 'undefined' ? localStorage.getItem('lava_token') : null
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('lava_token')
      localStorage.removeItem('lava_user')
      window.location.href = '/login'
    }
    throw new Error('Sessão expirada. Faça login novamente.')
  }

  if (!res.ok) {
    let msg = `Erro ${res.status}`
    try {
      const d = await res.json()
      if (typeof d.detail === 'string') {
        msg = d.detail
      } else if (Array.isArray(d.detail)) {
        // Erros de validação do FastAPI vêm como lista de objetos
        msg = d.detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join('; ') || msg
      } else if (d.detail) {
        msg = JSON.stringify(d.detail)
      }
    } catch { /* ignore */ }
    throw new Error(msg)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

async function requestBlob(method: string, path: string, body?: unknown): Promise<Blob> {
  const url = `${BASE_URL}${path}`
  const token = typeof window !== 'undefined' ? localStorage.getItem('lava_token') : null
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined })
  if (!res.ok) throw new Error(`Erro ${res.status}`)
  return res.blob()
}

export const auth = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; user_id: string; email: string; role: string; full_name: string }>(
      'POST', '/auth/login', { email, password }
    ),
  logout: () => request<void>('POST', '/auth/logout'),
  me: () => request<{ id: string; email: string; role: string; full_name: string; is_active: boolean }>('GET', '/auth/me'),
}

export const users = {
  list: () => request<import('@/types').User[]>('GET', '/users'),
  create: (data: unknown) => request<import('@/types').User>('POST', '/users', data),
  get: (id: string) => request<import('@/types').User>('GET', `/users/${id}`),
  update: (id: string, data: unknown) => request<import('@/types').User>('PUT', `/users/${id}`, data),
  delete: (id: string) => request<void>('DELETE', `/users/${id}`),
}

export const cameras = {
  list: () => request<import('@/types').Camera[]>('GET', '/cameras'),
  create: (data: unknown) => request<import('@/types').Camera>('POST', '/cameras', data),
  get: (id: string) => request<import('@/types').Camera>('GET', `/cameras/${id}`),
  update: (id: string, data: unknown) => request<import('@/types').Camera>('PUT', `/cameras/${id}`, data),
  delete: (id: string) => request<void>('DELETE', `/cameras/${id}`),
  testConnection: (data: unknown) =>
    request<{ success: boolean; message: string; frame_available: boolean }>('POST', '/cameras/test-connection', data),
  getFrame: (id: string) => request<{ image_base64: string; width: number; height: number }>('GET', `/cameras/${id}/frame`),
  getCountingLine: (id: string) => request<import('@/types').CountingLine>('GET', `/cameras/${id}/counting-line`),
  saveCountingLine: (id: string, data: unknown) =>
    request<import('@/types').CountingLine>('POST', `/cameras/${id}/counting-line`, data),
  getStatus: (id: string) => request<{ is_online: boolean; last_seen_at?: string }>('GET', `/cameras/${id}/status`),
}

export const events = {
  list: (filters: import('@/types').EventFilter) =>
    request<import('@/types').PaginatedResponse<import('@/types').VehicleEvent>>('GET', '/events', undefined, filters as Record<string, string | number | boolean | undefined>),
  create: (data: unknown) => request<import('@/types').VehicleEvent>('POST', '/events', data),
  get: (id: string) => request<import('@/types').VehicleEvent>('GET', `/events/${id}`),
  update: (id: string, data: unknown) => request<import('@/types').VehicleEvent>('PUT', `/events/${id}`, data),
  delete: (id: string) => request<void>('DELETE', `/events/${id}`),
  exportCSV: (filters: import('@/types').EventFilter) => requestBlob('POST', '/events/export/csv', filters),
  exportExcel: (filters: import('@/types').EventFilter) => requestBlob('POST', '/events/export/excel', filters),
}

export const dashboard = {
  getMetrics: () => request<import('@/types').DashboardMetrics>('GET', '/dashboard/metrics'),
}

export const system = {
  getLogs: (params?: Record<string, string | number | undefined>) =>
    request<import('@/types').PaginatedResponse<import('@/types').SystemLog>>('GET', '/system/logs', undefined, params),
  getSettings: () => request<import('@/types').AppSetting[]>('GET', '/system/settings'),
  updateSetting: (key: string, data: unknown) => request<import('@/types').AppSetting>('PUT', `/system/settings/${key}`, data),
  getWorkerStatus: () => request<{ status: string; timestamp: string; cameras: string[] }>('GET', '/system/worker-status'),
}
