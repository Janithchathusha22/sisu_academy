import {authClient} from './supabase'

const base = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function accessToken() {
  const {data, error} = await authClient().auth.getSession()
  if (error) throw new ApiError(error.message, 401)
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
    throw new ApiError('Cannot connect to the server. Please try again shortly.', 0)
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    if (response.status === 401) window.dispatchEvent(new Event('sisu-session-expired'))
    throw new ApiError(typeof detail.detail === 'string' ? detail.detail : `Request failed (${response.status})`, response.status)
  }
  return response.status === 204 ? null : response.json()
}

export async function currentSession() {
  const {data, error} = await authClient().auth.getSession()
  if (error) throw new ApiError(error.message, 401)
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
