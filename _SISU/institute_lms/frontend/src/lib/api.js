import {requireSupabase} from './supabase'

const base=(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'')

export async function api(path,{method='GET',body}={}){
  const {data:{session},error}=await requireSupabase().auth.getSession()
  if(error||!session?.access_token)throw Error('Sign in before using this feature')
  const response=await fetch(base+path,{
    method,
    headers:{Authorization:`Bearer ${session.access_token}`,...(body?{'Content-Type':'application/json'}:{})},
    ...(body?{body:JSON.stringify(body)}:{}),
  })
  if(!response.ok){
    const detail=await response.json().catch(()=>({}))
    throw Error(typeof detail.detail==='string'?detail.detail:`Request failed (${response.status})`)
  }
  return response.json()
}
