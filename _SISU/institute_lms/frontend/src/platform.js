import {dayKey} from './rules.js'
export const expiresAt = value => new Date(new Date(value).getTime()+30*86400000).toISOString()
export function prunePromotions(data, now=new Date()){
 const cutoff=now.getTime()-30*86400000
 for(const key of ['news','campaigns'])data[key]=data[key].filter(p=>new Date(p.published_at||p.creation||p.starts_on).getTime()>cutoff)
 // Inquiry and financial records have their own retention policies.
}
export function platformSummary(data, period='month'){
 const today=dayKey(),start=new Date(today+'T00:00:00Z')
 if(period==='week')start.setUTCDate(start.getUTCDate()-((start.getUTCDay()+6)%7))
 else if(period==='year'){start.setUTCMonth(0,1)}else start.setUTCDate(1)
 const from=start.toISOString().slice(0,10),inRange=d=>d&&d.slice(0,10)>=from&&d.slice(0,10)<=today
 const students=data.members.filter(m=>m.role==='Student'),teachers=data.members.filter(m=>m.role==='Teacher')
 const transactions=[...data.invoices.filter(i=>i.status==='Paid').map(i=>({date:i.paid_at,amount:i.amount,currency:'LKR',provider:data.institute.title,reference:i.name})),...data.marketplace.enrollments.filter(e=>e.status==='Paid').map(e=>({date:e.paid_at,amount:e.fee,currency:e.currency,provider:data.marketplace.providers.find(p=>p.name===e.provider)?.title,reference:e.receipt}))].filter(t=>inRange(t.date))
 const currencies={};transactions.forEach(t=>currencies[t.currency]=(currencies[t.currency]||0)+t.amount)
 const buckets=Array.from({length:period==='year'?12:period==='week'?7:new Date(start.getUTCFullYear(),start.getUTCMonth()+1,0).getDate()},(_,i)=>{const d=new Date(start);if(period==='year')d.setUTCMonth(i);else d.setUTCDate(d.getUTCDate()+i);const key=d.toISOString().slice(0,period==='year'?7:10);return {key,label:period==='year'?d.toLocaleDateString('en',{month:'short',timeZone:'UTC'}):String(d.getUTCDate()),students:students.filter(s=>s.joined_on?.startsWith(key)).length,transactions:transactions.filter(t=>t.date?.startsWith(key)).length}})
 return {period,from,to:today,studentCount:students.length,teacherCount:teachers.length,instituteCount:1+data.marketplace.providers.filter(p=>p.type==='Institute').length,independentCount:data.marketplace.providers.filter(p=>p.type==='Independent teacher').length,newStudents:students.filter(s=>inRange(s.joined_on)).length,newTeachers:teachers.filter(t=>inRange(t.joined_on)).length,transactions:transactions.slice().sort((a,b)=>b.date.localeCompare(a.date)),currencies,buckets,providers:[{title:data.institute.title,code:data.institute.code,country:'Sri Lanka',type:'Institute'},...data.marketplace.providers]}
}
