// Supabase authentication runs on FastAPI; access and refresh tokens stay server-side.
import {api, rememberSession, logoutSession} from './api'

export async function signIn(email, password) {
  return rememberSession(await api('/api/auth/login', {method: 'POST', body: {email, password}}))
}

export async function signUp({email, password, fullName, accountType = 'student', details = {}}) {
  return rememberSession(await api('/api/auth/signup', {
    method: 'POST',
    body: {...details, email, password, full_name: fullName, account_type: accountType},
  }))
}

export async function signInWithGoogle() {
  const {url} = await api('/api/auth/google/start', {method: 'POST'})
  const target = new URL(url)
  if (target.protocol !== 'https:') throw Error('Invalid authentication destination')
  location.assign(target.href)
}

export async function requestPasswordReset(email) {
  return api('/api/auth/password/reset', {method: 'POST', body: {email}})
}

export async function updatePassword(password) {
  return api('/api/auth/password', {method: 'PUT', body: {password}})
}

export const signOut = logoutSession
