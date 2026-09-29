import test from 'node:test'
import assert from 'node:assert/strict'
import {seed,sampleVideo} from '../src/demoExpanded.js'
import {insights} from '../src/analytics.js'
import {canAccess} from '../src/rules.js'
const data=seed(),admin=data.members.find(m=>m.role==='Admin')
test('360 synthetic learners, 12 teachers, 18 classrooms and unique institute IDs',()=>{
 assert.equal(data.members.filter(m=>m.role==='Student').length,360)
 assert.equal(data.members.filter(m=>m.role==='Teacher').length,12)
 assert.equal(data.rooms.length,18)
 assert.equal(new Set(data.members.map(m=>m.name)).size,data.members.length)
 assert(data.members.every(m=>m.user.endsWith('@example.invalid')))
 assert(data.members.filter(m=>m.role==='Student').every(m=>/^ST-SLDA-\d{5}$/.test(m.name)))
})
test('all enrollment references resolve and installment sums match the agreed fee',()=>{
 for(const e of data.enrollments){assert(data.rooms.some(r=>r.name===e.classroom));assert(data.members.some(m=>m.name===e.student));assert.equal(data.invoices.filter(i=>i.enrollment===e.name).reduce((s,i)=>s+i.amount,0),e.fee)}
 for(const r of data.rooms)assert.equal(r.students,data.enrollments.filter(e=>e.classroom===r.name).length)
})
test('institute totals derive from actual distinct records',()=>{
 const a=insights(data,admin);assert.equal(a.totals.students,360);assert.equal(a.categories.reduce((s,c)=>s+c.students,0),360)
 assert.equal(a.totals.collected,data.invoices.filter(i=>i.status==='Paid'&&i.paid_at.startsWith(a.month)).reduce((s,i)=>s+i.amount,0))
 assert(a.totals.collected>0);assert.equal(a.totals.classes,18)
})
test('teacher reports include only their classrooms, students, payments and campaigns',()=>{
 for(const t of data.members.filter(m=>m.role==='Teacher')){
 const a=insights(data,t),ids=new Set(data.rooms.filter(r=>r.teacher===t.name).map(r=>r.name));assert(a.rooms.every(r=>r.teacher===t.name));assert(a.progress.every(p=>ids.has(p.classroom)));assert(a.students.every(s=>data.enrollments.some(e=>e.student===s.name&&ids.has(e.classroom))));assert(a.campaigns.every(c=>c.teacher===t.name));assert.equal(a.teachers.length,1)
 }
})
test('student progress is personal and leaderboard only exposes aliases for their programme',()=>{
 const s=data.members[0],a=insights(data,s);assert(a.progress.every(p=>p.student===s.name));assert(a.students.every(m=>m.name===s.name));assert.equal(a.campaigns.length,0);assert.equal(a.leads.length,0);assert(a.leaderboard.every(r=>r.category===s.category&&!r.full_name&&!r.user));assert(a.ownRank.rank>0)
})
test('sample recording exists and default student has eligible access',()=>{
 assert.equal(sampleVideo,'YSul9yrAvN4');assert(data.materials.every(m=>m.youtube_id===sampleVideo));const e=data.enrollments[0];assert(canAccess(e,data.invoices.filter(i=>i.enrollment===e.name)).allowed)
})
test('large demo remains below conservative browser storage size',()=>assert(Buffer.byteLength(JSON.stringify(data),'utf8')<3_000_000))
