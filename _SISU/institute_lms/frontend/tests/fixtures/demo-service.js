import { seed } from './demoExpanded'
import {getBlob} from './materials/blobStore'
import { insights } from './analytics'
import { graphemes } from './rules'
import {demoScale} from './grades'
import {validateResults} from './resultImport'
import {keywords} from './discoveryRanking'
import { prunePromotions, platformSummary } from './platform'
import { youtubeVideoId, marketplaceSeed, validateProvider, nextProviderCode } from './marketplace'
import { canAccess, dayKey } from './rules'
export const isDemo = false
const key = 'sisu-demo-v2'
let data
try { data = isDemo ? JSON.parse(localStorage.getItem(key)) || seed() : null } catch { data = null }
if(isDemo&&data&&!data.marketplace)data.marketplace=marketplaceSeed()
if(isDemo&&data){
 if(!data.members.some(m=>m.role==='PlatformAdmin'))data.members.push({name:'PLATFORM-OWNER',role:'PlatformAdmin',full_name:'Platform Owner',user:'owner@example.invalid',active:1})
 if(!data.accountRequests)data.accountRequests=[]
 if(!data.membershipControlVersion){const academy=data.marketplace.providers.find(p=>p.name==='teen-academy');if(academy)academy.owner=data.members.find(m=>m.role==='Admin').name;data.membershipControlVersion=1}
 if(!data.discoveryInterests)data.discoveryInterests={}
 if(!data.marketplace.keywordVersion){const fresh=marketplaceSeed();for(const p of data.marketplace.providers)p.keywords=p.keywords||fresh.providers.find(x=>x.name===p.name)?.keywords||['education'];for(const c of data.marketplace.classes){const f=fresh.classes.find(x=>x.name===c.name);c.keywords=c.keywords||f?.keywords||['education'];c.active_learners_30d=c.active_learners_30d??f?.active_learners_30d??0}data.marketplace.keywordVersion=1}
 if(!data.academic)data.academic={unlocked:[],results:data.enrollments.filter(e=>data.rooms.find(r=>r.name===e.classroom)?.category==='University').map((e,i)=>({name:'RESULT-'+i,institute:data.institute.code,classroom:e.classroom,student:e.student,term:'Semester 1',credits:3,grade:['A','B+','B','A-'][i%4],points:[4,3.3,3,3.7][i%4],excluded:false}))}
 if(!data.quizState)data.quizState={unlocked:[],quizzes:[],completions:[],attempts:[]}
 if(!data.marketplace.invites)data.marketplace.invites=[{name:'TA-DEMO-INVITE',code:'TA0051-DEMO-TEACHER',provider:'teen-academy',provider_code:'TA0051',expires_at:new Date(Date.now()+7*86400000).toISOString(),status:'Active'}]
 if(!data.marketplace.memberships)data.marketplace.memberships=[]
 if(!data.marketplace.teachingModelVersion){const upgraded=marketplaceSeed();for(const p of upgraded.providers)if(!data.marketplace.providers.some(x=>x.name===p.name))data.marketplace.providers.push(p);for(const c of upgraded.classes){const old=data.marketplace.classes.find(x=>x.name===c.name);if(old){old.teacher_account=c.teacher_account;old.duration_months=c.duration_months;old.schedule=c.schedule}else data.marketplace.classes.push(c)}data.marketplace.memberships.push({name:'BA-DEMO-TEACHER',provider:'british-academy',provider_title:'British Academy · Demo',account:'TC-SLDA-0001',teacher_id:'TC-BA0051-0001',status:'Active'});data.marketplace.teachingModelVersion=1}
 if(!data.marketplace.regionalVersion){const seed=marketplaceSeed();for(const p of seed.providers){const old=data.marketplace.providers.find(x=>x.name===p.name);if(old){old.currency=old.currency||p.currency;old.timezone=old.timezone||p.timezone}else data.marketplace.providers.push(p)}for(const c of seed.classes)if(!data.marketplace.classes.some(x=>x.name===c.name))data.marketplace.classes.push(c);data.marketplace.regionalVersion=1}
 if(!data.fontUpgrade){const math=data.rooms.find(r=>r.name==='maths');if(math)math.font='handwritten';data.fontUpgrade=true} 
}
let role = 'Admin'
let account = null
const current = () => data.members.find(m => m.role === role && (!account || m.name === account))
const persist = () => localStorage.setItem(key, JSON.stringify(data))
const newId = () => crypto.randomUUID()
const scopeRooms = () => data.rooms.filter(r => role === 'Admin' || (role === 'Teacher' ? r.teacher === current().name : data.enrollments.some(e => e.classroom === r.name && e.student === current().name && e.active!==0)))
const decision = r => role !== 'Student' ? { allowed: true, reason: 'Classroom manager' } : canAccess(data.enrollments.find(e => e.classroom === r.name && e.student === current().name && e.active!==0), data.invoices.filter(i => i.classroom === r.name && i.student === current().name))
const event = (body, classroom, student=null) => {
 const room=data.rooms.find(r=>r.name===classroom)
 const recipients=[...new Set(data.enrollments.filter(e=>e.classroom===classroom&&e.active!==0&&(!student||e.student===student)).map(e=>e.student))]
 for(const id of recipients){
  const member=data.members.find(m=>m.name===id);if(!member?.active)continue
  let contact={};try{contact=JSON.parse(localStorage.getItem('sisu-contact:'+id))||{}}catch{}
  for(const channel of ['WhatsApp','Email'])data.notifications.unshift({name:newId(),body,channel,status:(channel==='Email'?contact.verified&&contact.email_opt_in:member.whatsapp_opt_in)?'Queued':'Skipped',creation:dayKey(),student:id,teacher:room?.teacher})
 }
}
export function switchRole(value, id=null) { role = value; account=id }
export function resetDemo() {localStorage.removeItem(key);location.reload()}
export async function call(method, args = {}, module = 'api') {
  if (!isDemo) {
    const response = await fetch(`/api/method/institute_lms.${module}.${method}`, { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || window.csrf_token || '' }, body: JSON.stringify(args) })
    const result = await response.json()
    if (!response.ok || result.exc) {
      let message = 'The request could not be completed.'
      try { message = JSON.parse(JSON.parse(result._server_messages)[0]).message.replace(/<[^>]*>/g, '') } catch { /* Keep safe generic error. */ }
      throw new Error(message)
    }
    return result.message
  }
  if (!current()?.active) throw Error('This membership is inactive. Contact the institute to restore access.')
  prunePromotions(data)
  const v = args.data || args
  let result
  switch (method) {
    case 'bootstrap': return { institute: data.institute, member: current(), mode: 'demo', personas: data.members.filter(m=>m.role===role && (role!=='Student'||[1,101,211,301,331].some(n=>m.name==='ST-SLDA-'+String(n).padStart(5,'0')))) }
    case 'insights': return insights(data,current())
    case 'video_courses': {
      const courses=data.rooms.filter(r=>r.category==='Online Courses'&&r.active!==0&&(role!=='Teacher'||r.teacher===current().name)).map(r=>{const enrolled=data.enrollments.some(e=>e.classroom===r.name&&e.student===current().name&&e.active!==0),allowed=role!=='Student'||(enrolled&&decision(r).allowed);return {...r,enrolled,access:{allowed},lessons:data.sessions.filter(s=>s.classroom===r.name&&s.status==='Completed'&&s.youtube_id).map(s=>allowed?s:{name:s.name,title:s.title,module:s.module})}})
      return {courses,completions:data.quizState.completions.filter(c=>c.student===current().name)}
    }
    case 'create_video_course': {
      if(!['Admin','Teacher'].includes(role)||!v.title?.trim()||v.title.length>120||!v.description?.trim()||v.description.length>1000||!Array.isArray(v.lessons)||!v.lessons.length||v.lessons.length>30)throw Error('Add a course title, description and 1–30 lessons')
      const teacher=data.members.find(m=>m.name===v.teacher&&m.role==='Teacher'&&m.active)
      if(!teacher||(role==='Teacher'&&teacher.name!==current().name))throw Error('Choose an authorized teacher')
      if(!Number.isFinite(Number(v.fee))||v.fee<0||v.fee>1000000||(v.fee>0&&v.fee<10))throw Error('Set a free course or a fee of LKR 10–1,000,000')
      for(const l of v.lessons)if(!l.module?.trim()||l.module.length>80||!l.title?.trim()||l.title.length>120||!youtubeVideoId(l.url)||(l.description||'').length>1000)throw Error('Each lesson needs a module, title and valid HTTPS YouTube URL')
      const name='COURSE-'+newId();data.rooms.push({name,title:v.title,subject:v.title,description:v.description,teacher:teacher.name,teacher_name:teacher.full_name,category:'Online Courses',medium:v.medium,fee:Number(v.fee),comments_enabled:1,active:1,font:'sans',color:'violet',students:0})
      v.lessons.forEach(l=>data.sessions.push({name:newId(),classroom:name,module:l.module,title:l.title,description:l.description,youtube_id:youtubeVideoId(l.url),mode:'Online',status:'Completed',starts_at:dayKey()+' 00:00:00',ends_at:dayKey()+' 00:01:00',comments:'Inherit'}));result=name;break
    }
    case 'enroll_video_course': {
      if(role!=='Student')throw Error('Student account required');const room=data.rooms.find(r=>r.name===args.classroom&&r.category==='Online Courses'&&r.active!==0);if(!room)throw Error('Course unavailable')
      if(data.enrollments.some(e=>e.student===current().name&&e.classroom===room.name))throw Error('You already have an enrollment record. Ask the institute to restore removed access.')
      const name=newId();data.enrollments.push({name,classroom:room.name,student:current().name,fee:room.fee,active:1,access_override:'Automatic'});room.students=(room.students||0)+1
      if(room.fee>0)data.invoices.push({name:newId(),enrollment:name,classroom:room.name,student:current().name,amount:room.fee,installment:1,status:'Unpaid',due_date:dayKey()})
      result=name;break
    }
    case 'academic_results': {
      const rooms=new Set(scopeRooms().map(r=>r.name))
      return {unlocked:data.academic.unlocked.includes(current().name),results:data.academic.results.filter(r=>rooms.has(r.classroom)&&(role!=='Student'||r.student===current().name)),students:role==='Student'?[]:data.members.filter(m=>m.role==='Student'&&data.enrollments.some(e=>e.student===m.name&&rooms.has(e.classroom))),enrollments:role==='Student'?[]:data.enrollments.filter(e=>rooms.has(e.classroom))}
    }
    case 'gpa_unlock': if(role!=='Student')throw Error('The GPA add-on belongs to student accounts');if(!data.academic.unlocked.includes(current().name))data.academic.unlocked.push(current().name);break
    case 'publish_results_bulk': {
      if(!['Admin','Teacher'].includes(role)||!Array.isArray(v.rows)||!v.rows.length||v.rows.length>1000)throw Error('Choose 1–1,000 results for your course')
      const first=v.rows[0]
      if(!scopeRooms().some(r=>r.name===first.classroom)||!first.term?.trim()||first.term.length>50||v.rows.some(r=>r.classroom!==first.classroom||r.term!==first.term))throw Error('Use one authorized course and term per upload')
      const rows=validateResults(v.rows,data.enrollments,first)
      if(rows.some(r=>r.errors.length))throw Error('Correct every invalid row before publishing')
      const replaced=rows.filter(r=>data.academic.results.some(x=>x.student===r.student&&x.classroom===r.classroom&&x.term===r.term))
      if(replaced.length&&v.replace!==true)throw Error('Confirm replacing existing results')
      const updates=rows.map(({errors,line,...r})=>({...r,name:newId(),institute:data.institute.code,points:demoScale[r.grade]}))
      data.academic.results=data.academic.results.filter(x=>!updates.some(r=>r.student===x.student&&r.classroom===x.classroom&&r.term===x.term)).concat(updates)
      result={count:updates.length};break
    }
    case 'publish_result': {
      if(!['Teacher','Admin'].includes(role)||!scopeRooms().some(r=>r.name===v.classroom)||!data.enrollments.some(e=>e.classroom===v.classroom&&e.student===v.student))throw Error('You may publish results only for your enrolled learners')
      if(!(v.grade in demoScale)||!Number.isFinite(Number(v.credits))||Number(v.credits)<=0||Number(v.credits)>60||!v.term?.trim()||v.term.length>50)throw Error('Provide a valid grade, credits and term')
      const old=data.academic.results.find(r=>r.classroom===v.classroom&&r.student===v.student&&r.term===v.term),row={...v,name:old?.name||newId(),institute:data.institute.code,points:demoScale[v.grade],excluded:!!v.excluded}
      if(old)Object.assign(old,row);else data.academic.results.push(row);break
    }
    case 'live_chat': {
      const session=data.sessions.find(s=>s.name===args.session),room=scopeRooms().find(r=>r.name===session?.classroom)
      if(!['Teacher','Admin'].includes(role)||!room)throw Error('Live chat is available only to this classroom’s teacher or institute admin')
      return {messages:[{id:'DEMO-CHAT-1',author:'Demo learner Anuki',text:'The worked example is clear. Thank you, teacher!',published_at:'Synthetic comment'},{id:'DEMO-CHAT-2',author:'Demo learner Kavindu',text:'Could you explain the second step once more?',published_at:'Synthetic comment'},{id:'DEMO-CHAT-3',author:'Demo learner Nethmi',text:'Can we try one more practice question?',published_at:'Synthetic comment'}],polling_interval_ms:15000,ended:false}
    }
    case 'platform_summary': if(role!=='PlatformAdmin')throw Error('Platform owner access required');return platformSummary(data,args.period)
    case 'quiz_workspace': {
      const names=new Set(scopeRooms().map(r=>r.name))
      return {unlocked:data.quizState.unlocked.includes(current().name),sessions:data.sessions.filter(s=>names.has(s.classroom)),quizzes:data.quizState.quizzes.filter(q=>names.has(q.classroom)).map(q=>role==='Student'?{...q,questions:q.questions.map(({answer,...rest})=>rest)}:q),attempts:data.quizState.attempts.filter(a=>role==='Student'?a.student===current().name:names.has(a.classroom))}
    }
    case 'quiz_unlock': throw Error('AI Quiz is coming soon')
    case 'save_manual_quiz': {
      if(!['Admin','Teacher'].includes(role)||!scopeRooms().some(r=>r.name===v.classroom))throw Error('Classroom unavailable')
      if(!data.sessions.some(s=>s.name===v.session&&s.classroom===v.classroom))throw Error('Choose a lesson in this classroom')
      if(!v.title?.trim()||!Array.isArray(v.questions)||v.questions.length<1||v.questions.length>10)throw Error('Add a title and 1–10 questions')
      for(const q of v.questions){if(!['True / False','Multiple choice'].includes(q.kind)||!q.prompt?.trim()||q.prompt.length>300||!Array.isArray(q.options)||q.options.length<2||q.options.length>6||q.options.some(o=>!o.trim()||o.length>150)||!Number.isInteger(q.answer)||q.answer<0||q.answer>=q.options.length)throw Error('Complete every question, answer option and correct answer')}
      data.quizState.quizzes=data.quizState.quizzes.filter(q=>q.session!==v.session)
      data.quizState.quizzes.push({...v,name:newId(),source:'Manual teacher quiz'});break
    }
    case 'complete_lesson': {
      const session=data.sessions.find(s=>s.name===args.session),room=scopeRooms().find(r=>r.name===session?.classroom)
      if(role!=='Student'||!room||!decision(room).allowed||session.status!=='Completed')throw Error('Complete an accessible lesson first')
      if(!data.quizState.completions.some(c=>c.session===session.name&&c.student===current().name))data.quizState.completions.push({session:session.name,student:current().name})
      let q=data.quizState.quizzes.find(q=>q.session===session.name)
      result=q?{...q,questions:q.questions.map(({answer,...rest})=>rest)}:null;break
    }
    case 'submit_lesson_quiz': {
      const q=data.quizState.quizzes.find(q=>q.session===args.session),room=scopeRooms().find(r=>r.name===q?.classroom)
      if(role!=='Student'||!q||!room||!decision(room).allowed||!data.quizState.completions.some(c=>c.session===args.session&&c.student===current().name))throw Error('Quiz unavailable')
      if(!Array.isArray(args.answers)||args.answers.length!==q.questions.length||q.questions.some((q,i)=>!Number.isInteger(args.answers[i])||args.answers[i]<0||args.answers[i]>=q.options.length))throw Error('Answer every question')
      const correct=q.questions.filter((q,i)=>q.answer===args.answers[i]).length
      result={name:newId(),student:current().name,classroom:q.classroom,session:q.session,title:q.title,source:q.source,correct,total:q.questions.length,score:Math.round(correct/q.questions.length*100),creation:dayKey(),questions:JSON.parse(JSON.stringify(q.questions)),answers:[...args.answers]}
      data.quizState.attempts.push(result);break
    }
    case 'account_controls': {
      const owned=data.marketplace.providers.filter(p=>p.owner===current().name),ids=new Set(['home',...owned.map(p=>p.name)])
      const home=role==='Admin'?data.members.filter(m=>m.role==='Teacher').map(m=>({name:'home:'+m.name,account:m.name,full_name:m.full_name,teacher_id:m.name,provider:'home',provider_title:data.institute.title,status:m.active?'Active':'Removed'})):[]
      return {providers:[{name:'home',title:data.institute.title},...owned.filter(p=>p.type==='Institute')],memberships:[...home,...data.marketplace.memberships.filter(m=>role==='Admin'?ids.has(m.provider):m.account===current().name).map(m=>({...m,full_name:data.members.find(p=>p.name===m.account)?.full_name||m.account}))],enrollments:role==='Student'?[]:data.enrollments.filter(e=>scopeRooms().some(r=>r.name===e.classroom)).map(e=>({...e,full_name:data.members.find(m=>m.name===e.student)?.full_name})),requests:data.accountRequests.filter(r=>r.account===current().name),owned_profiles:owned}
    }
    case 'account_action': {
      if(v.confirmation!=='CONFIRM'||!v.reason?.trim()||v.reason.length>500)throw Error('Confirm the action and give a reason')
      const owned=data.marketplace.providers.filter(p=>p.owner===current().name),ids=new Set(['home',...owned.map(p=>p.name)])
      if(['approve_teacher','remove_teacher','leave_institute'].includes(v.kind)){
        if(v.target.startsWith('home:')){if(role!=='Admin'||v.kind!=='remove_teacher')throw Error('Institute administrator required');const m=data.members.find(m=>m.name===v.target.slice(5)&&m.role==='Teacher');if(!m)throw Error('Teacher unavailable');m.active=0}
        else {const m=data.marketplace.memberships.find(m=>m.name===v.target);if(!m)throw Error('Membership unavailable');if(v.kind==='leave_institute'){if(m.account!==current().name)throw Error('Only your own membership can be changed');m.status='Removed'}else{if(role!=='Admin'||!ids.has(m.provider))throw Error('This institute is not yours');if(v.kind==='approve_teacher'&&(m.status!=='Pending'||v.verified!==true))throw Error('Verify the teacher before approval');m.status=v.kind==='approve_teacher'?'Active':'Removed'}}
      }else if(v.kind==='remove_student'){
        const e=data.enrollments.find(e=>e.name===v.target);if(!['Teacher','Admin'].includes(role)||!e||!scopeRooms().some(r=>r.name===e.classroom))throw Error('Only your classroom learners can be removed');e.active=0;e.access_override='Closed'
      }else if(v.kind==='remove_member'){
        if(role!=='Admin')throw Error('Institute administrator required');const m=data.members.find(m=>m.name===v.target&&m.role==='Student');if(!m)throw Error('Student unavailable');m.active=0;data.enrollments.filter(e=>e.student===m.name).forEach(e=>e.active=0)
      }else if(['delete_profile','delete_institute','delete_public_profile'].includes(v.kind)){
        if(v.kind==='delete_institute'&&role!=='Admin')throw Error('Institute administrator required')
        if(v.kind==='delete_profile'&&v.target!==current().name)throw Error('Only your own profile can be deleted')
        if(v.kind==='delete_public_profile'){const p=owned.find(p=>p.name===v.target);if(!p)throw Error('Only your own public profile can be deleted');p.deleted=true}
        if(!data.accountRequests.some(r=>r.account===current().name&&r.kind===v.kind&&r.target===v.target&&r.status==='Pending'))data.accountRequests.push({...v,name:newId(),account:current().name,status:'Pending',created_at:dayKey()})
      }else throw Error('Unknown account action')
      data.audits.push({...v,actor:current().name,at:new Date().toISOString()});break
    }
    case 'teacher_memberships': {
      const providers=[{name:'home',title:data.institute.title,code:data.institute.code},...data.marketplace.providers.filter(p=>p.type==='Institute'&&p.owner===current().name)]
      return {providers:role==='Admin'?providers:[],invites:role==='Admin'?data.marketplace.invites.filter(i=>providers.some(p=>p.name===i.provider)).map(({code,...rest})=>rest):[],memberships:data.marketplace.memberships.filter(m=>m.account===current().name)}
    }
    case 'issue_teacher_invite': {
      const provider=args.provider==='home'?data.institute:data.marketplace.providers.find(p=>p.name===args.provider&&p.type==='Institute'&&p.owner===current().name)
      if(role!=='Admin'||!provider)throw Error('Only the institute admin may issue invitations')
      result={name:newId(),code:provider.code+'-'+crypto.randomUUID().replaceAll('-',''),provider:args.provider,provider_code:provider.code,status:'Active',expires_at:new Date(Date.now()+7*86400000).toISOString()};data.marketplace.invites.push(result);break
    }
    case 'revoke_teacher_invite': {
      const invite=data.marketplace.invites.find(i=>i.name===args.name),allowed=invite&&(invite.provider==='home'||data.marketplace.providers.some(p=>p.name===invite.provider&&p.owner===current().name))
      if(role!=='Admin'||!allowed||invite.status!=='Active')throw Error('Invitation unavailable');invite.status='Revoked';break
    }
    case 'join_institute': {
      if(role!=='Teacher')throw Error('Sign in as a teacher to join an institute')
      const invite=data.marketplace.invites.find(i=>i.code===args.code.trim())
      if(!invite||invite.status!=='Active'||new Date(invite.expires_at)<=new Date())throw Error('This invitation is invalid, expired or already used')
      if(invite.provider==='home'||data.marketplace.memberships.some(m=>m.account===current().name&&m.provider===invite.provider))throw Error('You already belong to this institute')
      const p=invite.provider==='home'?data.institute:data.marketplace.providers.find(p=>p.name===invite.provider),n=data.marketplace.memberships.filter(m=>m.provider===invite.provider).length+1
      data.marketplace.memberships.push({name:newId(),provider:invite.provider,provider_title:p.title,account:current().name,teacher_id:'TC-'+p.code+'-'+String(n).padStart(4,'0'),status:'Pending'});invite.status='Used';break
    }
    case 'save_interests': if(role!=='Student')throw Error('Interests belong to student accounts');data.discoveryInterests[current().name]=keywords(args.interests,20);break
    case 'marketplace': return {...data.marketplace,providers:data.marketplace.providers.filter(p=>!p.deleted),classes:data.marketplace.classes.filter(c=>!data.marketplace.providers.find(p=>p.name===c.provider)?.deleted),interests:data.discoveryInterests[current().name]||[],engaged_keywords:role==='Student'?scopeRooms().map(r=>r.subject):[],enrollments:data.marketplace.enrollments.filter(e=>e.account===current().name&&e.active!==0)}
    case 'save_provider': {
      const old=v.name?data.marketplace.providers.find(p=>p.name===v.name):null
      if(v.name&&(!old||old.owner!==current().name))throw Error('Only the profile owner can edit this profile')
      validateProvider(v,data.marketplace.providers,old?.name)
      const profile={...v,name:old?.name||newId(),owner:current().name,code:old?.code||nextProviderCode(v.title,data.marketplace.providers),symbol:v.title.split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase(),country:v.country==='Other'?v.custom_country:v.country,education_system:v.education_system==='Custom education system'?v.custom_system:v.education_system}
      if(old)Object.assign(old,profile);else data.marketplace.providers.push(profile)
      result=profile;break
    }
    case 'marketplace_enroll': {
      if(role!=='Student')throw Error('Sign in as a student to enroll')
      const c=data.marketplace.classes.find(c=>c.name===args.classroom)
      if(!c)throw Error('Class unavailable')
      if(!['USD','LKR'].includes(c.currency))throw Error('Checkout for this currency is awaiting a configured exchange rate and payment gateway. No enrollment was charged.')
      if(data.marketplace.enrollments.some(e=>e.account===current().name&&e.classroom===c.name))return true
      const provider=data.marketplace.providers.find(p=>p.name===c.provider),prior=data.marketplace.enrollments.find(e=>e.account===current().name&&e.provider===c.provider)
      const count=new Set(data.marketplace.enrollments.filter(e=>e.provider===c.provider).map(e=>e.account)).size+1
      data.marketplace.enrollments.push({name:newId(),account:current().name,provider:c.provider,classroom:c.name,student_id:prior?.student_id||'ST-'+provider.code+'-'+String(count).padStart(5,'0'),status:'Unpaid',fee:c.fee,platform_fee:c.currency==='LKR'?300:1,amount_due:Number(c.fee)+(c.currency==='LKR'?300:1),currency:c.currency});break
    }
    case 'marketplace_demo_payment': {
      const enrollment=data.marketplace.enrollments.find(e=>e.account===current().name&&e.classroom===args.classroom)
      if(role!=='Student'||!enrollment)throw Error('Enrollment unavailable')
      enrollment.status='Paid';enrollment.paid_at=dayKey();enrollment.receipt='DEMO-'+enrollment.name.slice(0,8);break
    }
    case 'save_campaign': {
      if(role==='Student') throw Error('Teachers and administrators only')
      const room=scopeRooms().find(r=>r.name===v.classroom)
      if(!room || !v.headline?.trim() || !v.description?.trim()) throw Error('Choose a classroom and add your headline and description')
      if(graphemes(v.headline)>80||graphemes(v.description)>240) throw Error('Headline: 80 characters. Description: 240 characters.')
      if(!v.starts_on||!v.ends_on||v.ends_on<v.starts_on) throw Error('Choose a valid date range')
      if(!/^[A-Za-z0-9_-]{1,24}$/.test(v.code)) throw Error('Use a referral code of up to 24 letters, numbers, dashes or underscores')
      if(data.campaigns.some(c=>c.code.toLowerCase()===v.code.toLowerCase())) throw Error('This referral code is already in use')
      data.campaigns.unshift({...v,name:newId(),teacher:room.teacher,views:0,clicks:0,status:'Draft',published_at:new Date().toISOString()});break
    }
    case 'update_lead': {
      const lead=data.leads.find(l=>l.name===args.name),campaign=data.campaigns.find(c=>c.name===lead?.campaign)
      if(role==='Student'||!campaign||(role==='Teacher'&&campaign.teacher!==current().name))throw Error('Enquiry unavailable')
      if(!['New','Contacted','Trial booked','Enrolled'].includes(args.status))throw Error('Invalid enquiry stage')
      lead.status=args.status;break
    }
    case 'add_demo_lead': {
      const c=data.campaigns.find(c=>c.name===args.campaign)
      if(role==='Student'||!c||(role==='Teacher'&&c.teacher!==current().name))throw Error('Campaign unavailable')
      data.leads.unshift({name:newId(),campaign:c.name,alias:'New demo trial enquiry',status:'Trial booked',source:c.channel,creation:dayKey()});break
    }
    case 'dashboard_summary': { const list=await call('invoices');return {classrooms:scopeRooms().length,paid_count:list.filter(i=>i.status==='Paid').length,paid_total:list.filter(i=>i.status==='Paid').reduce((s,i)=>s+Number(i.amount),0),outstanding_total:list.filter(i=>i.status!=='Paid').reduce((s,i)=>s+Number(i.amount),0)} }
    case 'classrooms': return scopeRooms().filter(r => !args.search || r.title.toLowerCase().includes(args.search.toLowerCase()) || r.subject.toLowerCase().includes(args.search.toLowerCase())).map(r => ({ ...r, access: decision(r) }))
    case 'schedule': return data.sessions.filter(s => scopeRooms().some(r => r.name === s.classroom))
    case 'news': return data.news.filter(n => n.starts_on <= dayKey() && n.ends_on >= dayKey())
    case 'invoices': return data.invoices.filter(i => role === 'Admin' || (role === 'Student' ? i.student === current().name : scopeRooms().some(r => r.name === i.classroom)))
    case 'teachers': return data.members.filter(m=>m.role==='Teacher'&&(role==='Admin'||m.name===current().name))
    case 'set_member_active': { const m=data.members.find(m=>m.name===args.member_id);if(m.name===current().name)throw Error('You cannot deactivate yourself');m.active=args.active;break }
    case 'members': return data.members.filter(m => (!args.role || m.role === args.role) && (role==='Admin'||m.name===current().name||(role==='Teacher'&&data.enrollments.some(e=>e.student===m.name&&scopeRooms().some(r=>r.name===e.classroom)))))
    case 'notifications': return data.notifications.filter(n=>role==='Admin'||(role==='Student'?n.student===current().name:n.teacher===current().name))
    case 'enrollments': return data.enrollments.filter(e => e.classroom === args.classroom)
    case 'classroom_detail': {
      const room = scopeRooms().find(r => r.name === args.name)
      if (!room) throw Error('Classroom unavailable')
      const result = { room, access: decision(room) }
      for (const key of ['sessions', 'materials', 'feedback', 'announcements']) result[key] = result.access.allowed ? data[key].filter(item => item.classroom === room.name) : []
      return result
    }
    case 'save_classroom': {
      if (!v.title || !v.subject || !v.teacher) throw Error('Title, subject and teacher are required')
      result = v.name || newId()
      const old = data.rooms.find(r => r.name === result)
      const room = { ...v, name: result, color: old?.color || 'violet', active: 1, teacher_name: data.members.find(m => m.name === v.teacher)?.full_name, students: old?.students || 0 }
      if (old) Object.assign(old, room); else data.rooms.push(room)
      break
    }
    case 'save_session': {
      if (v.ends_at <= v.starts_at) throw Error('End time must be after start time')
      result = v.name || newId()
      const old = data.sessions.find(s => s.name === result)
      if (old) Object.assign(old, v); else data.sessions.push({ ...v, name: result })
      event(`Class schedule updated: ${v.title}`,v.classroom); break
    }
    case 'add_material': {
      const room=data.rooms.find(r=>r.name===v.classroom)
      if(!room||role==='Student'||role==='Teacher'&&room.teacher!==current().name)throw Error('Only this classroom teacher or an institute administrator can add materials')
      if(v.kind==='Document'&&v.file_id){
        const file=await getBlob(v.file_id)
        if(!file||file.classroom!==v.classroom||file.owner!==current().name)throw Error('Upload your own classroom document first')
        if(!['View only','Downloadable'].includes(v.download_policy))throw Error('Choose the student access policy')
        if(v.file_type!=='pdf'&&v.download_policy==='View only'&&!v.preview_file_id)throw Error('Add a matching PDF preview for view-only Office files')
        if(v.preview_file_id){const pdf=await getBlob(v.preview_file_id);if(!pdf||pdf.file_type!=='pdf'||pdf.classroom!==v.classroom||pdf.owner!==current().name)throw Error('Upload a matching PDF preview')}
      }
      data.materials.unshift({ ...v, name: newId(), youtube_id: v.kind === 'Recording' ? v.url.match(/(?:v=|youtu.be\/|live\/|embed\/)([\w-]{11})/)?.[1] || v.url : '' }); event(`New material: ${v.title}`,v.classroom); break
    }
    case 'post_announcement': data.announcements.unshift({ ...v, name: newId() }); event(v.headline,v.classroom); break
    case 'post_feedback': {
      const session = data.sessions.find(s => s.name === args.session)
      const room = data.rooms.find(r => r.name === session.classroom)
      if (Date.parse(session.ends_at.replace(' ','T')+'+05:30')>Date.now() || session.comments === 'Disabled' || (session.comments !== 'Enabled' && !room.comments_enabled)) throw Error('Comments are disabled or the session has not ended')
      data.feedback.unshift({ ...args, classroom: session.classroom, student: current().name, name: newId(), creation: dayKey() }); break
    }
    case 'publish_news': if (!v.images?.length || v.images.length > 5 || v.ends_on < v.starts_on) throw Error('Add 1–5 images and a valid date range'); data.news.unshift({ ...v, name: newId(),published_at:new Date().toISOString() }); break
    case 'add_member': {
      if(v.role==='Student')throw Error('Students must sign up themselves. Share your profile so they can request membership.')
      if (data.members.some(m => m.user === v.user)) throw Error('This email is already registered')
      const prefix = v.role === 'Student' ? 'ST' : v.role === 'Teacher' ? 'TC' : 'AD'
      result = `${prefix}-${data.institute.code}-${String(data.members.filter(m => m.role === v.role).length+1).padStart(v.role === 'Student' ? 5 : 4, '0')}`
      data.members.push({ ...v, name: result, active: 1, alias:'Learner '+result.split('-').at(-1),joined_on:dayKey() }); break
    }
    case 'enroll': {
      if (data.enrollments.some(e => e.classroom === v.classroom && e.student === v.student)) throw Error('Student is already enrolled')
      const room = data.rooms.find(r => r.name === v.classroom)
      if (Number(room.fee) && Math.round(v.installments.reduce((s,i)=>s+Number(i.amount),0)*100) !== Math.round(room.fee*100)) throw Error('Installments must total the class fee')
      result = newId(); data.enrollments.push({ name: result, ...v, active: 1, fee: room.fee, access_override: 'Automatic' })
      v.installments.forEach((i,index) => data.invoices.push({ ...i, name: newId(), enrollment: result, classroom: room.name, student: v.student, installment: index+1, status: 'Unpaid' })); break
    }
    case 'set_access': { const e = data.enrollments.find(e => e.name === args.enrollment); if (!args.reason) throw Error('Provide a reason'); data.audits.push({ ...args, at: new Date().toISOString(), before: { ...e } }); Object.assign(e, { access_override: args.override, grace_until: args.grace_until }); break }
    case 'checkout': throw Error('Preview mode: no money is collected. Connect payments.lk on your Frappe site to accept payments.')
    case 'demo_payment': { const invoice = data.invoices.find(i => i.name === args.invoice); invoice.status = 'Paid'; invoice.receipt_number = `DEMO-RC-${invoice.name}`; invoice.paid_at = dayKey(); event(`Demo payment received: LKR ${invoice.amount}.`,invoice.classroom,invoice.student); break }
    case 'save_branding': Object.assign(data.institute, v); break
    case 'notification_preferences': Object.assign(current(), args, { whatsapp_opt_in: args.opted_in }); break
    case 'summary': { const active = data.members.filter(m => m.role === 'Student' && m.active).length; return { active_students: active, included: 500, extra_students: Math.max(0,active-500), base_fee: data.institute.base_fee, extra_fee: Math.max(0,active-500)*50, total: data.institute.base_fee+Math.max(0,active-500)*50, history: [] } }
    case 'connect': case 'schedule_broadcast': case 'sync_broadcast': case 'transition_broadcast': throw Error('Connect your Google OAuth credentials on the Frappe site to manage YouTube Live. No broadcast is created in preview mode.')
    default: throw Error('This action is unavailable')
  }
  persist(); return result
}
export async function uploadImage(file) {
  if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 5*1024*1024) throw Error('Choose a PNG, JPEG or WebP image up to 5 MB')
  // Resize and re-encode raster uploads before storage.
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, 1600 / bitmap.width, 1600 / bitmap.height)
  const canvas = document.createElement('canvas'); canvas.width = Math.round(bitmap.width*scale); canvas.height = Math.round(bitmap.height*scale)
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height); bitmap.close()
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/webp', .82))
  if (isDemo) return canvas.toDataURL('image/webp', .82)
  const form = new FormData(); form.append('file', blob, 'image.webp'); form.append('is_private', '0')
  const response = await fetch('/api/method/upload_file', { method: 'POST', credentials: 'same-origin', body: form, headers: { 'X-Frappe-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || '' } })
  if (!response.ok) throw Error('Image upload failed')
  return (await response.json()).message.file_url
}
