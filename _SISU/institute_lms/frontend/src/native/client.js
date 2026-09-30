import {previewMode} from '../preview/mode'
import {requestRoute} from '../lib/api'
export async function request(module, method, args = {}, verb = 'POST') {
  if (previewMode) {
    const {previewRequest}=await import('../preview/adapter')
    return structuredClone(await previewRequest(module,method,args))
  }
  return requestRoute(module,method,args,verb)
}
