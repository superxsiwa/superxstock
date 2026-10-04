import { useAppStore } from './store'

export async function apiRequest(url, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = useAppStore.getState().accessToken

  if (options.body instanceof URLSearchParams) {
    headers.set('Content-Type', 'application/x-www-form-urlencoded')
  } else if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token && !url.startsWith('/api/auth/')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(url, { ...options, headers })
  const payload = await response.json().catch(() => ({}))
  if (response.status === 401 && !url.startsWith('/api/auth/')) {
    useAppStore.getState().logout()
    useAppStore.getState().setAuthOpen(true)
  }
  if (!response.ok) throw new Error(payload.detail || 'Request failed')
  return payload
}