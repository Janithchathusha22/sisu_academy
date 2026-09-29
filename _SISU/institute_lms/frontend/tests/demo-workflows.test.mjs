import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {pathToFileURL,fileURLToPath} from 'node:url'
import {resolve,dirname} from 'node:path'

test('demo workflows: review membership, bulk results, video enrollment and lesson completion',async()=>{
 const storage=new Map();globalThis.localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)};globalThis.location={hostname:'localhost'}
 const dir=resolve(dirname(fileURLToPath(import.meta.url)),'../src')
 let source=await readFile(resolve(dir,'../tests/fixtures/demo-service.js'),'utf8')
 source=source.replace('export const isDemo = false','export const isDemo = true').replace(/from '\.\/([^']+)'/g,(_,name)=>"from '"+pathToFileURL(resolve(dir,name.endsWith('.js')?name:name+'.js')).href+"'")
 const {call,switchRole}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))
 switchRole('Teacher');const teacher=(await call('bootstrap')).member
 await call('join_institute',{code:'TA0051-DEMO-TEACHER'})
 let member=(await call('teacher_memberships')).memberships.find(m=>m.provider==='teen-academy');assert.equal(member.status,'Pending')
 await assert.rejects(call('account_action',{data:{kind:'approve_teacher',target:member.name,verified:true,reason:'Reviewed',confirmation:'CONFIRM'}}))
 switchRole('Admin');await call('account_action',{data:{kind:'approve_teacher',target:member.name,verified:true,reason:'Demo identity review',confirmation:'CONFIRM'}})
 switchRole('Teacher');assert.equal((await call('teacher_memberships')).memberships.find(m=>m.name===member.name).status,'Active')
 await assert.rejects(call('join_institute',{code:'TA0051-DEMO-TEACHER'}))
 const a=await call('academic_results'),e=a.enrollments[0],base={classroom:e.classroom,term:'QA term',credits:3,grade:'A',student:e.student}
 await assert.rejects(call('publish_results_bulk',{data:{rows:[base,{...base,student:'FOREIGN'}]}}));assert.equal((await call('academic_results')).results.filter(r=>r.term==='QA term').length,0)
 assert.equal((await call('publish_results_bulk',{data:{rows:[base]}})).count,1)
 await assert.rejects(call('publish_results_bulk',{data:{rows:[base]}}))
 await call('publish_results_bulk',{data:{rows:[{...base,grade:'B'}],replace:true}})
 const course=await call('create_video_course',{data:{title:'QA course',description:'A synthetic free video course',teacher:teacher.name,medium:'English',fee:0,lessons:[{module:'Welcome',title:'Demo lesson',url:'https://youtu.be/YSul9yrAvN4',description:'Playback demo'}]}})
 switchRole('Student',e.student);await call('enroll_video_course',{classroom:course});const c=(await call('video_courses')).courses.find(c=>c.name===course);assert(c.access.allowed)
 await call('complete_lesson',{session:c.lessons[0].name});assert((await call('video_courses')).completions.some(x=>x.session===c.lessons[0].name))
 // A verified learner receives an email queue entry for an enrolled class only.
 localStorage.setItem('sisu-contact:'+e.student,JSON.stringify({verified:true,email_opt_in:true,email:'student@example.invalid'}))
 switchRole('Teacher');await call('save_session',{data:{classroom:course,title:'Notification QA',starts_at:'2026-10-01 10:00',ends_at:'2026-10-01 11:00'}})
 switchRole('Student',e.student)
 const messages=(await call('notifications')).filter(n=>n.body.includes('Notification QA'))
 assert.equal(messages.length,2);assert(messages.every(n=>n.student===e.student))
 assert.equal(messages.find(n=>n.channel==='Email').status,'Queued')
 await call('save_interests',{interests:['Mathematics','Arabic']});assert.deepEqual((await call('marketplace')).interests,['mathematics','arabic'])
 await assert.rejects(call('create_video_course',{data:{}}))
})
