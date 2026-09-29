import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {community,createProfile,approveProfile,relationship,changeLink} from './fixtures/community.js'

function storage(){const data=new Map();globalThis.localStorage={getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)};globalThis.window={dispatchEvent(){}}}
test('public identity is unique and verified profiles require owner review after editing',()=>{
 storage()
 const profile=createProfile({user:'qa@example.invalid',username:'qatutor',display_name:'QA Tutor',kind:'Teacher',country:'Sri Lanka'})
 assert.equal(profile.status,'Pending');assert.equal(profile.code,'')
 assert.throws(()=>createProfile({...profile,user:'other@example.invalid'}),/taken/)
 const verified=approveProfile(profile.name,'Verified');assert.match(verified.code,/^QT\d{7}$/)
 assert.throws(()=>createProfile({...profile,username:'different'}),/permanent/)
 assert.equal(createProfile({...profile,bio:'Updated'}).status,'Pending')
})
test('following is distinct from membership and leaving one preserves the other',()=>{
 storage();const follow=relationship('teen-academy','student-qa','Follow'),join=relationship('teen-academy','student-qa','Student join')
 assert.equal(follow.status,'Active');assert.equal(join.status,'Pending');assert.notEqual(follow.name,join.name)
 changeLink(join.name,'Active');changeLink(join.name,'Left')
 assert.equal(community().links.find(l=>l.name===follow.name).status,'Active')
})
test('payout preview reserves once, releases rejected funds and blocks repeat completion',async()=>{
 storage()
 const text=(await readFile(new URL('./fixtures/walletClient.js',import.meta.url),'utf8')).replace("import {isDemo,call} from '../service'",'const isDemo=true;const call=()=>{throw Error("Unexpected live request")}')
 const {walletCall}=await import('data:text/javascript;base64,'+Buffer.from(text).toString('base64'))
 const teacher={name:'TC-SLDA-0001',role:'Teacher'},owner={name:'OWNER',role:'PlatformAdmin'}
 await assert.rejects(walletCall('dashboard',{wallet:'W-INSTITUTE'},teacher),/unavailable/)
 const m=await walletCall('submit_method',{wallet:'W-NIMAL',data:{kind:'Local Bank',account:'0000000000'}},teacher)
 await assert.rejects(walletCall('request_payout',{wallet:'W-NIMAL',method:m.name,amount:6000,request_key:'qa-1'},teacher),/approval/)
 await walletCall('review_method',{method:m.name,decision:'Approved',reason:'Fictional QA'},owner)
 const args={wallet:'W-NIMAL',method:m.name,amount:6000,request_key:'qa-1'}
 const req=await walletCall('request_payout',args,teacher);await walletCall('request_payout',args,teacher)
 let d=await walletCall('dashboard',{},teacher);assert.equal(d.wallet.held_minor,600000);assert.equal(d.ledger.length,1)
 await walletCall('update_payout',{request:req.name,status:'Rejected',reason:'Fictional QA'},owner)
 d=await walletCall('dashboard',{},teacher);assert.equal(d.wallet.available_minor,4250000);assert.equal(d.wallet.held_minor,0)
 const next=await walletCall('request_payout',{...args,request_key:'qa-2'},teacher)
 await walletCall('update_payout',{request:next.name,status:'Processing'},owner)
 await walletCall('update_payout',{request:next.name,status:'Completed',reference:'QA-FAKE-TX'},owner)
 await assert.rejects(walletCall('update_payout',{request:next.name,status:'Completed',reference:'QA-FAKE-TX'},owner),/transition/)
 d=await walletCall('dashboard',{},teacher);assert.equal(d.wallet.available_minor,3650000);assert.equal(d.wallet.held_minor,0)
})
