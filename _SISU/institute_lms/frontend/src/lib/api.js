import {authClient, clearLocalSession} from './supabase'
import {safeApiErrorMessage} from './api-errors.js'

const base = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status, code = '') {
    super(message)
    this.status = status
    this.code = code
  }
}

async function accessToken() {
  const {data, error} = await authClient().auth.getSession()
  if (error) throw new ApiError(safeApiErrorMessage(401), 401)
  return data.session?.access_token || ''
}

export async function api(path, {method = 'GET', body} = {}) {
  const token = await accessToken()
  let response
  try {
    response = await fetch(base + path, {
      method,
      cache: 'no-store',
      headers: {
        ...(body ? {'Content-Type': 'application/json'} : {}),
        ...(token ? {Authorization: `Bearer ${token}`} : {}),
      },
      ...(body ? {body: JSON.stringify(body)} : {}),
    })
  } catch {
    throw new ApiError(safeApiErrorMessage(0), 0)
  }
  if (!response.ok) {
    let code = ''
    let detail = {}
    try {
      const payload = await response.json()
      detail = typeof payload?.detail === 'object' ? payload.detail : {}
      code = detail.code || ''
    } catch { /* The status fallback remains safe for non-JSON failures. */ }
    if (response.status === 401 && code !== 'session_not_yet_valid') {
      window.dispatchEvent(new Event('sisu-session-expired'))
      await clearLocalSession().catch(() => {})
    }
    throw new ApiError(safeApiErrorMessage(response.status, code, detail), response.status, code)
  }
  return response.status === 204 ? null : response.json()
}

export async function currentSession() {
  const {data, error} = await authClient().auth.getSession()
  if (error) throw new ApiError(safeApiErrorMessage(401), 401)
  if (!data.session) throw new ApiError('Authentication required', 401)
  const profile = await api('/api/me')
  return {user: data.session.user, profile, access_token: data.session.access_token}
}

export async function logoutSession() {
  const {error} = await authClient().auth.signOut()
  if (error) throw new ApiError(error.message, 400)
}

export async function requestRoute(module, method) {
  throw new Error(`The ${module}.${method} feature is not enabled in the active portal.`)
}
