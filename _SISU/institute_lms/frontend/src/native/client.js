import {previewMode} from '../preview/mode'
export async function request(module, method, args = {}, verb = 'POST') {
  if (import.meta.env.DEV && previewMode) {
    const {previewRequest}=await import('../preview/adapter')
    return structuredClone(await previewRequest(module,method,args))
  }
  const url = `/api/method/institute_lms.${module}.${method}`
  const response = await fetch(url + (verb === 'GET' ? '?' + new URLSearchParams(args) : ''), {
    method: verb, credentials: 'same-origin', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': window.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || '' },
    ...(verb === 'POST' ? { body: JSON.stringify(args) } : {}),
  })
  if (!response.headers.get('content-type')?.includes('application/json')) throw Error('The Frappe service is not connected to this preview yet.')
  const data = await response.json()
  if (!response.ok || data.exc) {
    let message = 'The request could not be completed. Check your access and try again.'
    try { message = JSON.parse(JSON.parse(data._server_messages)[0]).message.replace(/<[^>]*>/g, '') } catch {}
    throw Error(message)
  }
  return data.message
}
