import {requireSupabase} from './supabase'

const apiBase=String(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'')
const enc=value=>encodeURIComponent(String(value))
const payload=args=>args?.data??args??{}
const omit=(source,...keys)=>Object.fromEntries(Object.entries(source||{}).filter(([key,value])=>!keys.includes(key)&&value!==undefined&&value!==null&&value!==''))
const read=(path,query={})=>({path,method:'GET',query})
const write=(path,body,method='POST')=>({path,method,body})

export const routeMap={
  'portal_session.current':()=>read('/api/me'),
  'portal_session.overview':()=>read('/api/dashboard/summary'),
  'api.bootstrap':()=>read('/api/dashboard/bootstrap'),
  'api.dashboard_summary':()=>read('/api/dashboard/summary'),
  'api.classrooms':args=>read('/api/classes',args),
  'api.classroom_detail':args=>read(`/api/classes/${enc(args.name)}`,omit(args,'name')),
  'api.save_classroom':args=>{const data=payload(args);return data.name?write(`/api/classes/${enc(data.name)}`,omit(data,'name'),'PUT'):write('/api/classes',data)},
  'api.set_classroom_deleted':args=>Number(args.deleted)?write(`/api/classes/${enc(args.name)}`,undefined,'DELETE'):write(`/api/classes/${enc(args.name)}/restore`,{}),
  'api.schedule':args=>read('/api/sessions',args),
  'api.save_session':args=>{const data=payload(args);return data.name?write(`/api/sessions/${enc(data.name)}`,omit(data,'name'),'PUT'):write('/api/sessions',data)},
  'api.news':args=>read('/api/news',args),
  'api.publish_news':args=>write('/api/news',payload(args)),
  'api.invoices':args=>read('/api/invoices',args),
  'api.notifications':args=>read('/api/notifications',args),
  'api.members':args=>read('/api/members',args),
  'api.add_member':args=>write('/api/members',payload(args)),
  'api.set_member_active':args=>write(`/api/members/${enc(args.member_id)}`,{active:Boolean(args.active)},'PATCH'),
  'api.teachers':args=>read('/api/teachers',args),
  'api.enrollments':args=>read('/api/enrollments',args),
  'api.enroll':args=>write('/api/enrollments',payload(args)),
  'api.set_access':args=>write(`/api/enrollments/${enc(args.enrollment)}`,omit(args,'enrollment'),'PATCH'),
  'teaching.programmes':args=>read('/api/programmes',args),
  'teaching.save_programme':args=>{const data=payload(args);return data.name?write(`/api/programmes/${enc(data.name)}`,omit(data,'name'),'PUT'):write('/api/programmes',data)},
  'teaching.enroll_programme':args=>write(`/api/programmes/${enc(args.programme)}/enroll`,{}),
  'profiles.me':()=>read('/api/profiles/me'),
  'profiles.save_profile':args=>write('/api/profiles/me',payload(args),'PUT'),
  'profiles.search':args=>read('/api/profiles',args),
  'profiles.pending':args=>read('/api/profiles',{...args,status:'pending'}),
  'profiles.review':args=>write(`/api/profiles/${enc(args.profile)}/review`,omit(args,'profile'),'PATCH'),
  'catalog.publishing_options':args=>read('/api/profiles',{...args,publishing_options:true}),
  'catalog.detail':args=>read(`/api/profiles/${enc(args.profile)}`),
}

function queryString(values){
  const query=new URLSearchParams()
  for(const [key,value] of Object.entries(values||{})){
    if(value===undefined||value===null||value==='')continue
    if(Array.isArray(value))for(const item of value)query.append(key,String(item))
    else query.set(key,typeof value==='object'?JSON.stringify(value):String(value))
  }
  const text=query.toString()
  return text?'?'+text:''
}

function errorMessage(data,status){
  if(typeof data?.detail==='string')return data.detail
  if(Array.isArray(data?.detail))return data.detail.map(item=>item.msg||String(item)).join(' · ')
  if(typeof data?.message==='string')return data.message
  return `Request failed (${status})`
}

export async function api(path,{method='GET',query,body,responseType='json',headers={}}={}){
  const {data:{session},error}=await requireSupabase().auth.getSession()
  if(error)throw error
  if(!session?.access_token)throw Error('Sign in before using this feature')
  const response=await fetch(apiBase+path+queryString(query),{
    method,
    cache:'no-store',
    headers:{Authorization:`Bearer ${session.access_token}`,...(body!==undefined&&!(body instanceof FormData)?{'Content-Type':'application/json'}:{}),...headers},
    ...(body!==undefined?{body:body instanceof FormData?body:JSON.stringify(body)}:{}),
  })
  if(!response.ok){
    const detail=await response.json().catch(()=>({}))
    throw Error(errorMessage(detail,response.status))
  }
  if(response.status===204)return null
  if(responseType==='blob')return response.blob()
  return response.json()
}

export async function requestRoute(module,method,args={}){
  const key=`${module}.${method}`
  const resolve=routeMap[key]
  if(!resolve)throw Error(`This feature is waiting for its FastAPI route (${key}).`)
  const target=resolve(args||{})
  return api(target.path,target)
}
