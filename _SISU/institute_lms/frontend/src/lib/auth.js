import {requireSupabase} from './supabase'

function redirectUrl(hash=''){
  const url=new URL(import.meta.env.BASE_URL||'/',location.origin)
  url.hash=hash
  return url.href
}

export async function restoreSession(){
  const {data,error}=await requireSupabase().auth.getSession()
  if(error)throw error
  return data.session
}

export function onAuthStateChange(callback){
  const {data}=requireSupabase().auth.onAuthStateChange((event,session)=>callback(event,session))
  return ()=>data.subscription.unsubscribe()
}

export async function signInWithGoogle(){
  const {data,error}=await requireSupabase().auth.signInWithOAuth({provider:'google',options:{redirectTo:redirectUrl()}})
  if(error)throw error
  return data
}

export async function signInWithPassword(email,password){
  const {data,error}=await requireSupabase().auth.signInWithPassword({email:email.trim().toLowerCase(),password})
  if(error)throw error
  return data
}

export async function sendPasswordReset(email){
  const {data,error}=await requireSupabase().auth.resetPasswordForEmail(email.trim().toLowerCase(),{redirectTo:redirectUrl('settings')})
  if(error)throw error
  return data
}

export async function signOut(){
  const {error}=await requireSupabase().auth.signOut()
  if(error)throw error
}
