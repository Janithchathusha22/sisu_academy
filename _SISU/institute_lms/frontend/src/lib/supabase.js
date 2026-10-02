import {createClient} from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL?.trim()
const publishableKey = (
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY
)?.trim()

// One browser client owns the persisted Supabase session and token refresh.
export const supabase = url && publishableKey ? createClient(url, publishableKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
}) : null

export function authClient() {
  if (!supabase) throw new Error('Supabase authentication is not configured.')
  return supabase
}

function result(data, error) {
  if (error) throw error
  return data
}

export async function signIn(email, password) {
  const {data, error} = await authClient().auth.signInWithPassword({email, password})
  return result(data, error)
}

export async function signUp({email, password, fullName, accountType = 'student', details = {}}) {
  const {data, error} = await authClient().auth.signUp({
    email,
    password,
    options: {
      data: {...details, full_name: fullName, account_type: accountType},
    },
  })
  return result(data, error)
}

export async function signInWithGoogle() {
  const {data, error} = await authClient().auth.signInWithOAuth({
    provider: 'google',
    options: {redirectTo: `${location.origin}${import.meta.env.BASE_URL || '/'}`},
  })
  return result(data, error)
}

export async function requestPasswordReset(email) {
  const {error} = await authClient().auth.resetPasswordForEmail(email, {
    redirectTo: `${location.origin}${import.meta.env.BASE_URL || '/'}`,
  })
  if (error) throw error
  return {message: 'If an account exists, a reset link will be sent.'}
}

export async function updatePassword(password) {
  const {error} = await authClient().auth.updateUser({password})
  if (error) throw error
  await authClient().auth.signOut({scope: 'global'})
  return {message: 'Password updated. Sign in with your new password.'}
}

export async function signOut() {
  const {error} = await authClient().auth.signOut()
  if (error) throw error
}
