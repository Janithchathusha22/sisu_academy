import {currentSession} from './api'
import {authClient, requestPasswordReset, signIn, signInWithGoogle, signOut} from './supabase'

export const restoreSession = currentSession
export const sendPasswordReset = requestPasswordReset
export {signOut}

export function onAuthStateChange(callback) {
  const {data} = authClient().auth.onAuthStateChange((event, session) => callback(event, session))
  return () => data.subscription.unsubscribe()
}

export async function signInWithPassword(email, password) {
  const data = await signIn(email, password)
  return {data, session: data.session}
}
