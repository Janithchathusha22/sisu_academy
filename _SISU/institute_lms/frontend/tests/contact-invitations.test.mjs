import test from 'node:test'
import assert from 'node:assert/strict'
const storage=new Map()
globalThis.sessionStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)}
const {previewRequest:call,selectPreviewRole:role,resetPreview,loadAcademy}=await import('../src/preview/adapter.js')

test('guardian contacts need permission but no OTP; adult contacts still require verification',async()=>{
 resetPreview();loadAcademy();role('Student')
 const d={date_of_birth:'2015-01-01',notification_language:'en',whatsapp_phone:'+94770000000',whatsapp_opt_in:true}
 await assert.rejects(call('private_contact','save_details',{data:d}),/guardian/)
 Object.assign(d,{guardian_name:'Example guardian',guardian_relationship:'Mother',guardian_phone:d.whatsapp_phone,guardian_permission:true})
 await call('private_contact','save_details',{data:d})
 assert.equal((await call('private_contact','get_details')).verified_phone,'')
 await assert.rejects(call('private_contact','save_details',{data:{...d,guardian_permission:false}}),/permission/)
 await assert.rejects(call('private_contact','save_details',{data:{...d,whatsapp_phone:'+94770000001'}}),/guardian/)
 d.date_of_birth='2000-01-01'
 await assert.rejects(call('private_contact','save_details',{data:d}),/Verify/)
 await call('private_contact','request_whatsapp_code',{phone:d.whatsapp_phone})
 await assert.rejects(call('mobile_verification','verify',{code:'000000'}),/did not match/)
 await call('mobile_verification','verify',{code:'123456'})
 await call('private_contact','save_details',{data:d})
 assert.equal((await call('private_contact','get_details')).data.guardian_name,'Example guardian')
 role('Teacher');assert.equal((await call('private_contact','get_details')).data.guardian_name,undefined)
 assert.ok((await call('profiles','search')).every(p=>p.guardian_name===undefined&&p.date_of_birth===undefined))
})
test('email invitation recipient and roles are enforced and acceptance cannot repeat',async()=>{
 resetPreview();loadAcademy();role('Student')
 await assert.rejects(call('invitations','invite_teacher',{email:'teacher@admin.com'}),/Provider/)
 role('Admin');const invite=await call('invitations','invite_teacher',{email:'teacher@admin.com'})
 await assert.rejects(call('invitations','invite_teacher',{email:'teacher@admin.com'}),/already pending/)
 const other=await call('invitations','invite_teacher',{email:'other@example.invalid'})
 role('Teacher');assert.equal((await call('invitations','list_invitations')).length,1)
 await assert.rejects(call('invitations','respond',{name:other.name,decision:'Accepted'}),/unavailable/)
 assert.equal((await call('invitations','respond',{name:invite.name,decision:'Accepted'})).status,'Accepted')
 await assert.rejects(call('invitations','respond',{name:invite.name,decision:'Accepted'}),/unavailable/)
})
