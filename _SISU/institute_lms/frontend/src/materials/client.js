import {previewMode} from '../preview/mode'
import {call,isDemo} from '../service'
import {saveBlob,getBlob} from './blobStore'
export const MAX_DOCUMENT_SIZE=10*1024*1024
export async function uploadDocument(file,classroom,member,purpose='original'){
 const suffix=file.name.split('.').at(-1).toLowerCase()
 if(!['pdf','ppt','pptx','doc','docx'].includes(suffix)||purpose==='preview'&&suffix!=='pdf')throw Error('Choose PDF, PPT/PPTX or DOC/DOCX. A preview must be PDF.')
 if(!file.size||file.size>MAX_DOCUMENT_SIZE)throw Error('Choose a nonempty document of at most 10 MB.')
 const head=new Uint8Array(await file.slice(0,8).arrayBuffer())
 if(suffix==='pdf'&&String.fromCharCode(...head.slice(0,5))!=='%PDF-')throw Error('This file is not a PDF.')
 if(['pptx','docx'].includes(suffix)&&(head[0]!==80||head[1]!==75))throw Error('Invalid Office file. Save as PPTX or DOCX and try again.')
 if(['ppt','doc'].includes(suffix)&&[208,207,17,224,161,177,26,225].some((n,i)=>head[i]!==n))throw Error('Invalid legacy Office file.')
 if(isDemo){const id=crypto.randomUUID();await saveBlob({id,blob:file,filename:file.name,file_type:suffix,file_size:file.size,classroom,owner:member.name});return {file_id:id,filename:file.name,file_type:suffix,file_size:file.size}}
 const body=new FormData();body.append('file',file);body.append('classroom',classroom);body.append('purpose',purpose)
 if(previewMode)throw Error('This action requires the connected server. No data was sent.');const response=await fetch('/api/method/institute_lms.materials.upload',{method:'POST',credentials:'same-origin',headers:{'X-Frappe-CSRF-Token':document.querySelector('meta[name="csrf-token"]')?.content||window.csrf_token||''},body})
 const result=await response.json();if(!response.ok||result.exc)throw Error('Document upload failed. Check file type, size, classroom permission and your connection.');return result.message
}
export async function materialBlob(material,action,member){
 if(isDemo){
  const detail=await call('classroom_detail',{name:material.classroom})
  if(!detail.access.allowed)throw Error('Classroom access is required')
  const current=detail.materials.find(m=>m.name===material.name);if(!current)throw Error('Material unavailable')
  if(action==='download'&&member.role==='Student'&&current.download_policy!=='Downloadable')throw Error('Your teacher has made this material view only')
  const id=action==='download'||current.file_type==='pdf'?current.file_id:current.preview_file_id
  const record=await getBlob(id);if(!record||record.classroom!==current.classroom)throw Error('File is missing from this browser. Ask the teacher to upload it again.')
  return record.blob
 }
 if(previewMode)throw Error('This action requires the connected server. No data was sent.');const response=await fetch('/api/method/institute_lms.materials.content?'+new URLSearchParams({material:material.name,action}),{credentials:'same-origin',cache:'no-store'})
 if(!response.ok)throw Error('This material is unavailable. Check your class access or ask your teacher.')
 const blob=await response.blob();if(blob.size>MAX_DOCUMENT_SIZE)throw Error('Document exceeds the 10 MB viewing limit');return blob
}
