import { dayKey } from './rules.js'
const sum=(rows,key)=>rows.reduce((s,r)=>s+Number(r[key]||0),0)
const avg=(rows,key)=>rows.length?Math.round(sum(rows,key)/rows.length):0
export function insights(data, member) {
  const rooms=data.rooms.filter(r=>member.role==='Admin'||(member.role==='Teacher'?r.teacher===member.name:data.enrollments.some(e=>e.classroom===r.name&&e.student===member.name)))
  const roomIds=new Set(rooms.map(r=>r.name))
  const enrollments=data.enrollments.filter(e=>e.active&&roomIds.has(e.classroom)&&(member.role!=='Student'||e.student===member.name))
  const studentIds=new Set(enrollments.map(e=>e.student))
  const students=data.members.filter(m=>m.role==='Student'&&(member.role==='Admin'||studentIds.has(m.name)))
  const invoices=data.invoices.filter(i=>roomIds.has(i.classroom)&&(member.role!=='Student'||i.student===member.name))
  const ids=new Set(enrollments.map(e=>e.name)),records=data.progress.filter(p=>ids.has(p.enrollment))
  const month=dayKey().slice(0,7),monthly=records.filter(p=>p.month===month)
  const paid=invoices.filter(i=>i.status==='Paid'),currentPaid=paid.filter(i=>i.paid_at?.startsWith(month))
  const categories=[...new Set(rooms.map(r=>r.category||'Other'))].map(name=>({name,classes:rooms.filter(r=>r.category===name).length,students:new Set(enrollments.filter(e=>rooms.some(r=>r.name===e.classroom&&r.category===name)).map(e=>e.student)).size}))
  const teachers=data.members.filter(m=>m.role==='Teacher'&&(member.role==='Admin'||m.name===member.name)).map(t=>{
    const ids=new Set(rooms.filter(r=>r.teacher===t.name).map(r=>r.name)),p=records.filter(p=>ids.has(p.classroom)),inv=currentPaid.filter(i=>ids.has(i.classroom))
    return {...t,classes:ids.size,students:new Set(enrollments.filter(e=>ids.has(e.classroom)).map(e=>e.student)).size,paid:sum(inv,'amount'),progress:p.length?Math.round(sum(p,'completed')/sum(p,'total')*100):0}
  })
  const revenue=Array.from({length:6},(_,i)=>{const d=new Date(dayKey()+'T12:00:00');d.setDate(1);d.setMonth(d.getMonth()-5+i);const key=dayKey(d).slice(0,7);return {key,label:d.toLocaleDateString('en',{month:'short'}),amount:sum(paid.filter(x=>x.paid_at?.startsWith(key)),'amount')}})
  const competitionPool=data.members.filter(m=>m.role==='Student'&&(member.role==='Student'?m.category===member.category:studentIds.has(m.name)))
  const leaderboard=competitionPool.map(s=>{
    const p=data.progress.filter(p=>p.student===s.name&&p.month===month&&(member.role!=='Teacher'||roomIds.has(p.classroom)))
    const completion=p.length?Math.round(sum(p,'monthly_completed')/sum(p,'monthly_total')*100):0
    return {alias:s.alias,student:s.name,category:s.category,score:Math.round(avg(p,'quiz')*.5+completion*.3+avg(p,'attendance')*.2),completion}
  }).sort((a,b)=>b.score-a.score||a.student.localeCompare(b.student)).map((s,i)=>({...s,rank:i+1}))
  const campaigns=member.role==='Student'?[]:data.campaigns.filter(c=>member.role==='Admin'||c.teacher===member.name)
  const leads=data.leads.filter(l=>campaigns.some(c=>c.name===l.campaign))
  return {rooms,students,teachers,categories,revenue,leaderboard,campaigns,leads,month,
    totals:{students:students.filter(s=>s.active).length,teachers:teachers.length,classes:rooms.length,collected:sum(currentPaid,'amount'),outstanding:sum(invoices.filter(i=>i.status!=='Paid'),'amount'),overdue:invoices.filter(i=>i.status==='Overdue').length,progress:records.length?Math.round(sum(records,'completed')/sum(records,'total')*100):0,completion:monthly.length?Math.round(sum(monthly,'monthly_completed')/sum(monthly,'monthly_total')*100):0,attendance:avg(records,'attendance')},
    progress:records.map(p=>({...p,subject:rooms.find(r=>r.name===p.classroom)?.subject})),ownRank:leaderboard.find(s=>s.student===member.name)}
}
