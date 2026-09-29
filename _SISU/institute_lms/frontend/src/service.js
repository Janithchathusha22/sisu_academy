import {previewMode} from './preview/mode'
import {request} from './native/client'
export const isDemo = false
export const call=(method,args={},module='api')=>request(module,method,args)
export function switchRole(){throw Error('Role selection is resolved by your authenticated session.')}
export function resetDemo(){throw Error('Sample workspaces have been retired.')}
export async function uploadImage(file) {
  if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 5*1024*1024) throw Error('Choose a PNG, JPEG or WebP image up to 5 MB')
  // Resize and re-encode raster uploads before storage.
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, 1600 / bitmap.width, 1600 / bitmap.height)
  const canvas = document.createElement('canvas'); canvas.width = Math.round(bitmap.width*scale); canvas.height = Math.round(bitmap.height*scale)
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height); bitmap.close()
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/webp', .82))
  const form = new FormData(); form.append('file', blob, 'image.webp'); form.append('is_private', '0')
  if(previewMode)return canvas.toDataURL('image/webp',.82);
  const response = await fetch('/api/method/upload_file', { method: 'POST', credentials: 'same-origin', body: form, headers: { 'X-Frappe-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || '' } })
  if (!response.ok) throw Error('Image upload failed')
  return (await response.json()).message.file_url
}
