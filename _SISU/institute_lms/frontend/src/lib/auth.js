import {currentSession, logoutSession} from './api'
import {requestPasswordReset, signIn, signInWithGoogle} from './supabase'

export const restoreSession = currentSession
export const sendPasswordReset = requestPasswordReset
export const signOut = logoutSession

export function onAuthStateChange(callback) {
  const handleExpired = () => callback('SIGNED_OUT', null)
  window.addEventListener('sisu-session-expired', handleExpired)
  return () => window.removeEventListener('sisu-session-expired', handleExpired)
}

export async function signInWithPassword(email, password) {
  const session = await signIn(email, password)
  return {data: session, session}
}
