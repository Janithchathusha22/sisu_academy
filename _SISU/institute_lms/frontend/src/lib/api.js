const base=(import.meta.env?.VITE_API_BASE_URL||'').replace(/\/$/,'')
let csrf=''
export class ApiError extends Error {
  constructor(message,status){super(message);this.status=status}
}
export function rememberSession(result){csrf=result?.csrf_token||'';return result}
export async function api(path,{method='GET',body}={}){
  let response
  try{
    response=await fetch(base+path,{
      method,credentials:'include',cache:'no-store',
      headers:{...(body?{'Content-Type':'application/json'}:{}),...(!['GET','HEAD'].includes(method)&&csrf?{'X-CSRF-Token':csrf}:{})},
      ...(body?{body:JSON.stringify(body)}:{}),
    })
  }catch{throw new ApiError('Cannot connect to the server. Please try again shortly.',0)}
  if(!response.ok){
    const detail=await response.json().catch(()=>({}))
    if(response.status===401&&!path.startsWith('/api/auth/')){
      csrf='';window.dispatchEvent(new Event('sisu-session-expired'))
    }
    throw new ApiError(typeof detail.detail==='string'?detail.detail:`Request failed (${response.status})`,response.status)
  }
  return response.status===204?null:response.json()
}
export async function currentSession(){
  const hadSession=Boolean(csrf)
  try{return rememberSession(await api('/api/auth/session'))}
  catch(e){if(e.status===401){csrf='';if(hadSession)window.dispatchEvent(new Event('sisu-session-expired'))}throw e}
}
export async function logoutSession(){await api('/api/auth/session',{method:'DELETE'});csrf=''}
