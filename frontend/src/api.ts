const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export type ApiEnvelope<T> = { success?: boolean; data?: T; message?: string; request_id?: string }
export type Token = { access_token: string; refresh_token: string; token_type: string }
type ErrorField = { field?: string; message?: string }
type ValidationDetail = { loc?: Array<string | number>; msg?: string }
type ApiErrorPayload = {
  error?: { fields?: ErrorField[]; message?: string }
  detail?: string | ValidationDetail[]
}

type ApiRequestOptions = RequestInit & { skipAuth?: boolean; noRetry?: boolean }

function unwrap<T>(payload: ApiEnvelope<T> | T): T {
  if (payload && typeof payload === 'object' && 'data' in payload && payload.data !== undefined) return payload.data as T
  return payload as T
}
function errorMessage(payload: ApiErrorPayload): string {
  const fields = payload.error?.fields
  if (Array.isArray(fields) && fields.length) return fields.map(field => `${field.field || 'field'}: ${field.message || 'Invalid value'}`).join(' ')
  if (Array.isArray(payload.detail)) return payload.detail.map(item => `${(item.loc || []).join('.') || 'field'}: ${item.msg || 'Invalid value'}`).join(' ')
  return payload.error?.message || (typeof payload.detail === 'string' ? payload.detail : undefined) || 'The API request failed.'
}

function logoutOnUnauthorized() {
  if (localStorage.getItem('api_studio_access_token')) {
    localStorage.removeItem('api_studio_access_token')
    localStorage.removeItem('api_studio_refresh_token')
    window.location.reload()
  }
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = localStorage.getItem('api_studio_refresh_token')
  if (!refresh) return false

  try {
    const token = await request<Token>('/api/v1/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refresh }),
      skipAuth: true,
      noRetry: true,
    })
    localStorage.setItem('api_studio_access_token', token.access_token)
    localStorage.setItem('api_studio_refresh_token', token.refresh_token)
    return true
  } catch {
    return false
  }
}

async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { skipAuth, noRetry, ...fetchOptions } = options
  const headers = new Headers(fetchOptions.headers)
  headers.set('Content-Type', 'application/json')

  if (!skipAuth) {
    const access = localStorage.getItem('api_studio_access_token')
    if (access) headers.set('Authorization', `Bearer ${access}`)
  }

  const controller = new AbortController(); const timeout = window.setTimeout(() => controller.abort(), 10000)
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers, signal: controller.signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('The backend took too long to respond. Check that PostgreSQL is running.')
    throw error
  } finally {
    window.clearTimeout(timeout)
  }

  if (response.status === 204) return undefined as T
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && !noRetry) {
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        return request<T>(path, { ...options, noRetry: true })
      }
      logoutOnUnauthorized()
    }
    const message = errorMessage(payload)
    throw new Error(message)
  }

  return unwrap(payload)
}

const body = (value: unknown): RequestInit => ({ body: JSON.stringify(value) })
export const api = {
  auth: { register: (value: unknown) => request('/api/v1/auth/register', { method: 'POST', ...body(value) }), login: (value: unknown) => request<Token>('/api/v1/auth/login', { method: 'POST', ...body(value) }), refresh: (value: unknown) => request<Token>('/api/v1/auth/refresh', { method: 'POST', ...body(value) }), me: () => request('/api/v1/auth/me') },
  collections: { list: () => request('/api/v1/collections'), get: (id: string) => request(`/api/v1/collections/${id}`), create: (value: unknown) => request('/api/v1/collections', { method: 'POST', ...body(value) }), update: (id: string, value: unknown) => request(`/api/v1/collections/${id}`, { method: 'PATCH', ...body(value) }), remove: (id: string) => request(`/api/v1/collections/${id}`, { method: 'DELETE' }), favorite: (id: string, active: boolean) => request(`/api/v1/collections/${id}/favorite`, { method: active ? 'POST' : 'DELETE' }) },
  requests: { list: () => request('/api/v1/requests'), get: (id: string) => request(`/api/v1/requests/${id}`), create: (value: unknown) => request('/api/v1/requests', { method: 'POST', ...body(value) }), update: (id: string, value: unknown) => request(`/api/v1/requests/${id}`, { method: 'PATCH', ...body(value) }), remove: (id: string) => request(`/api/v1/requests/${id}`, { method: 'DELETE' }), execute: (id: string, value?: unknown) => request(`/api/v1/requests/${id}/execute`, { method: 'POST', ...body(value || {}) }), history: (id: string) => request(`/api/v1/requests/${id}/history`) },
  environments: { list: () => request('/api/v1/environments'), get: (id: string) => request<any>(`/api/v1/environments/${id}`), create: (value: unknown) => request('/api/v1/environments', { method: 'POST', ...body(value) }), update: (id: string, value: unknown) => request(`/api/v1/environments/${id}`, { method: 'PATCH', ...body(value) }), remove: (id: string) => request(`/api/v1/environments/${id}`, { method: 'DELETE' }), activate: (id: string) => request(`/api/v1/environments/${id}/activate`, { method: 'POST' }), deactivate: () => request('/api/v1/environments/deactivate', { method: 'POST' }) },
  history: {
    list: (params?: any) => {
      const query = new URLSearchParams()
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined && v !== null) {
            if (Array.isArray(v)) {
              v.forEach(val => query.append(k, String(val)))
            } else {
              query.append(k, String(v))
            }
          }
        })
      }
      return request(`/api/v1/history?${query.toString()}`)
    },
    get: (id: string) => request(`/api/v1/history/${id}`),
    replay: (id: string) => request(`/api/v1/history/${id}/replay`, { method: 'POST' }),
  },
  ai: { chat: (value: unknown) => request('/api/v1/ai/chat', { method: 'POST', ...body(value) }), generateRequest: (value: unknown) => request('/api/v1/ai/generate-request', { method: 'POST', ...body(value) }), explainResponse: (value: unknown) => request('/api/v1/ai/explain-response', { method: 'POST', ...body(value) }), generateCode: (value: unknown) => request('/api/v1/ai/generate-code', { method: 'POST', ...body(value) }), document: (value: unknown) => request('/api/v1/ai/document', { method: 'POST', ...body(value) }), search: (value: unknown) => request('/api/v1/ai/search', { method: 'POST', ...body(value) }) },
  imports: { postman: (value: unknown) => request('/api/v1/import/postman', { method: 'POST', ...body(value) }), openapi: (value: unknown) => request('/api/v1/import/openapi', { method: 'POST', ...body(value) }), curl: (value: unknown) => request('/api/v1/import/curl', { method: 'POST', ...body(value) }) },
  exports: { postman: (id: string) => request(`/api/v1/export/postman/${id}`), openapi: (id: string) => request(`/api/v1/export/openapi/${id}`), curl: (id: string) => request(`/api/v1/export/curl/${id}`) },
}
