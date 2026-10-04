import { useAppStore } from './store'
import i18n from './i18n'

const backendErrorKeys = new Map([
  ['Incorrect email or password', 'errors.invalidCredentials'],
  ['Email already registered', 'errors.emailRegistered'],
  ['Not enough cash for this purchase', 'errors.insufficientCash'],
  ['Not enough shares to sell', 'errors.insufficientShares'],
  ['Unsupported action', 'errors.unsupportedAction'],
])

function getApiErrorMessage(payload, status) {
  if (status === 422) return i18n.t('errors.invalidInput')

  const detail = payload?.detail
  if (typeof detail === 'string') {
    const messageKey = backendErrorKeys.get(detail)
    if (messageKey) return i18n.t(messageKey)

    const missingSymbol = /^Symbol (.+) not found$/.exec(detail)
    if (missingSymbol) return i18n.t('errors.symbolNotFound', { symbol: missingSymbol[1] })
  }

  return i18n.t('errors.generic')
}

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

  let response
  try {
    response = await fetch(url, { ...options, headers })
  } catch {
    throw new Error(i18n.t('errors.network'))
  }
  const payload = await response.json().catch(() => ({}))
  if (response.status === 401 && !url.startsWith('/api/auth/')) {
    useAppStore.getState().logout()
    useAppStore.getState().setAuthOpen(true)
  }
  if (!response.ok) throw new Error(getApiErrorMessage(payload, response.status))
  return payload
}