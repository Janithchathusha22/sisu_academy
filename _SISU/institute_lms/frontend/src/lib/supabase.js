import {createClient} from '@supabase/supabase-js'

const url=import.meta.env.VITE_SUPABASE_URL
const key=import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

export const supabase=url&&key?createClient(url,key):null

export function requireSupabase(){
  if(!supabase)throw Error('Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY in frontend/.env.local')
  return supabase
}

export async function signIn(email,password){
  const {data,error}=await requireSupabase().auth.signInWithPassword({email,password})
  if(error)throw error
  return data
}

export async function signOut(){
  const {error}=await requireSupabase().auth.signOut()
  if(error)throw error
}
