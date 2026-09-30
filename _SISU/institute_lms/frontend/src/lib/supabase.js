import {createClient} from '@supabase/supabase-js'

let client

function configuration(){
  const url=String(import.meta.env.VITE_SUPABASE_URL||'').trim()
  const key=String(import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY||'').trim()
  if(!url||!key)throw Error('Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY in frontend/.env.local')
  let parsed
  try{parsed=new URL(url)}catch{throw Error('VITE_SUPABASE_URL must be a valid HTTP or HTTPS URL')}
  if(!['http:','https:'].includes(parsed.protocol))throw Error('VITE_SUPABASE_URL must be a valid HTTP or HTTPS URL')
  return {url:parsed.href.replace(/\/$/,''),key}
}

export function hasSupabaseConfiguration(){
  return Boolean(import.meta.env.VITE_SUPABASE_URL&&import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY)
}

export function requireSupabase(){
  if(!client){
    const {url,key}=configuration()
    client=createClient(url,key,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}})
  }
  return client
}
