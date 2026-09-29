import {providerSocials} from '../commerce/socials.js'
import {academy} from './academy.js'
// Local interaction sandbox. No credentials, seeded students or provider calls.
const roles={Student:{name:'preview-student',role:'Student',full_name:'Student preview',user:'student@admin.com'},Teacher:{name:'preview-teacher',role:'Teacher',full_name:'Teacher preview',user:'teacher@admin.com'},Admin:{name:'preview-institute',role:'Admin',full_name:'Institute preview',user:'institute@admin.com'}}
let role='Student'
const initial=()=>({institute:{name:'preview-workspace',title:'Your institute',code:'PREVIEW',language:'en',accent:'#9874ba'},rooms:[],sessions:[],news:[],invoices:[],notifications:[],papers:[],attempts:[],profiles:[],links:[],assignments:[],tickets:[],replies:[],attendance:[],grants:[]})
let db=initial()
try{const saved=JSON.parse(sessionStorage.getItem('sisu-interface-preview-v1'));if(saved?.version===1)db=saved.data}catch{}
const persist=()=>sessionStorage.setItem('sisu-interface-preview-v1',JSON.stringify({version:1,data:db}))
const id=prefix=>prefix+'-'+crypto.randomUUID().slice(0,8)
const own=()=>roles[role]||{name:'preview-owner',role:'PlatformAdmin',full_name:'Owner preview',user:'superadmin@admin.com'}
const blankMoney={classrooms:0,paid_total:0,outstanding_total:0,paid_count:0,unpaid_count:0}
export function selectPreviewRole(value){if(!['Student','Teacher','Admin','Super Admin'].includes(value))throw Error('Unknown preview role');role=value}
export function loadAcademy(){if(db.scenario!=='teen-academy-v1'){sessionStorage.setItem('sisu-preview-before-academy',JSON.stringify(db));db=academy(roles);persist()}else{roles.Admin.full_name='Teen Academy';roles.Teacher.full_name='Nimal Perera';roles.Student.full_name='Amaya Fernando'}}
export function resetPreview(){db=initial();persist()}
function rights(r){const personal=r.owner_type==='Teacher',owner=role==='Teacher'&&personal&&r.owner_user===own().user,assigned=role==='Teacher'&&r.teacher===own().name&&r.teacher_assignment_active!==0;const manage=owner||role==='Admin'&&!personal||assigned&&r.teacher_access==='Full control';return {teach:owner||role==='Admin'&&!personal||assigned,edit:manage,delete:manage,assign:role==='Admin'&&!personal,fees:manage}}
function visible(r){return role==='Admin'?r.owner_type!=='Teacher':role==='Teacher'?rights(r).teach:(db.enrollments||[]).some(e=>e.classroom===r.name&&e.student===own().name&&e.active)}
function roomView(r){const enrolled=(db.enrollments||[]).find(e=>e.classroom===r.name&&e.student===own().name),paid=role!=='Student'||(db.invoices||[]).some(i=>i.student===own().name&&(r.programme?i.programme===r.programme:i.classroom===r.name)&&i.status==='Paid'&&(r.billing_type!=='Monthly'||i.billing_month===new Date().toISOString().slice(0,7)));const teacher=(db.teachers||[]).find(t=>t.name===r.teacher),profile=db.profiles.find(p=>p.kind==='Teacher'&&p.status==='Verified'&&p.user===teacher?.user);return {...r,teacher_profile:profile?{kind:'Teacher',display_name:profile.display_name,qualifications:profile.qualifications,profile_image:profile.profile_image,socials:providerSocials('Teacher',profile.socials)}:null,permissions:rights(r),students:(db.enrollments||[]).filter(e=>e.classroom===r.name&&e.active).length,access:{allowed:paid||enrolled?.access_override==='Open',reason:paid?'Paid enrollment':'Payment required'}}}
function result(value){persist();return structuredClone(value??null)}
function find(list,name){const row=list.find(x=>x.name===name);if(!row)throw Error('This preview record is no longer available.');return row}
export async function previewRequest(module,method,args={}){
 args=JSON.parse(JSON.stringify(args));
 const v=args.data||args,member=own()
 if(module==='private_contact'){
  db.privateContacts||={};db.verifiedPhones||={};db.phoneChallenges||={}
  if(method==='get_details')return {data:db.privateContacts[member.user]||{notification_language:'en'},verified_phone:db.verifiedPhones[member.user]||'',login_email:member.user}
  if(method==='request_whatsapp_code'){if(!/^\+[1-9][0-9]{7,14}$/.test(args.phone))throw Error('Use an international phone number');db.phoneChallenges[member.user]={phone:args.phone,expires:Date.now()+600000,attempts:0};return result({sent:true,preview:true})}
  if(method==='save_details'){
   const dob=v.date_of_birth,b=dob?new Date(dob+'T12:00:00'):null,n=new Date(),age=b?n.getFullYear()-b.getFullYear()-((n.getMonth()<b.getMonth()||n.getMonth()===b.getMonth()&&n.getDate()<b.getDate())?1:0):null
   if(role==='Student'&&age===null)throw Error('Add your birthday')
   if(b&&(isNaN(b.getTime())||b>n||age>120))throw Error('Enter a valid birthday')
   for(const key of ['contact_phone','guardian_phone','whatsapp_phone'])if(v[key]&&!/^\+[1-9][0-9]{7,14}$/.test(v[key]))throw Error('Use phone numbers with country code')
   if(role==='Student'&&age<16){if(!v.guardian_name||!v.guardian_relationship||!v.guardian_phone)throw Error('Students under 16 need guardian details');if(v.whatsapp_opt_in&&(!v.guardian_permission||v.whatsapp_phone!==v.guardian_phone))throw Error('Use the guardian number with their permission')}
   if(v.whatsapp_opt_in&&!(role==='Student'&&age!==null&&age<16&&v.guardian_permission&&v.whatsapp_phone===v.guardian_phone)&&v.whatsapp_phone!==db.verifiedPhones[member.user])throw Error('Verify your WhatsApp number first')
   db.privateContacts[member.user]={...v};return result({saved:true,age})
  }
 }
 if(module==='mobile_verification'&&method==='verify'){
  const challenge=db.phoneChallenges?.[member.user];if(!challenge||Date.now()>=challenge.expires||challenge.attempts>=5)throw Error('Code expired. Request another code');challenge.attempts++;persist();if(args.code!=='123456')throw Error('Code did not match');db.verifiedPhones[member.user]=challenge.phone;delete db.phoneChallenges[member.user];return result({verified:true})
 }
 if(module==='contact'){
  db.emailContacts||={};db.emailChallenges||={};const current=db.emailContacts[member.user]||{email:'',verified:false,email_opt_in:false,calendar:{status:'Disconnected'}}
  if(method==='status')return current
  if(method==='request_verification'){db.emailChallenges[member.user]={email:args.email,expires:Date.now()+600000,attempts:0};return result({sent:true,preview:true})}
  if(method==='verify'){const c=db.emailChallenges[member.user];if(!c||Date.now()>c.expires||c.attempts>=5)throw Error('Code expired');c.attempts++;persist();if(args.code!=='123456')throw Error('Code did not match');db.emailContacts[member.user]={...current,email:c.email,verified:true,email_opt_in:false};delete db.emailChallenges[member.user];return result({verified:true})}
  if(method==='preferences'){if(!current.verified)throw Error('Verify your email first');db.emailContacts[member.user]={...current,email_opt_in:!!args.email_opt_in};return result({saved:true})}
 }
 if(module==='invitations'){
  if(!['Admin','Teacher'].includes(role))throw Error('Provider account required')
  db.invitations||=[]
  if(method==='list_invitations')return db.invitations.filter(r=>role==='Admin'?r.institute===db.institute.name:r.invite_email===member.user).map(r=>({...r,expired:Date.parse(r.expires_at)<=Date.now()}))
  if(method==='invite_teacher'){
   if(role!=='Admin')throw Error('Institute administrator required');const email=String(args.email).trim().toLowerCase();if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))throw Error('Enter a valid email')
   if(db.invitations.some(r=>r.invite_email===email&&r.status==='Pending'&&Date.parse(r.expires_at)>Date.now()))throw Error('An invitation is already pending')
   const row={name:id('invite'),invite_email:email,institute:db.institute.name,profile:'teen-academy',institute_title:db.institute.title,status:'Pending',expires_at:new Date(Date.now()+7*86400000).toISOString()};db.invitations.push(row);return result({name:row.name})
  }
  if(role!=='Teacher')throw Error('Teacher account required')
  if(method==='respond'){
   const r=find(db.invitations,args.name);if(r.invite_email!==member.user||r.status!=='Pending'||Date.parse(r.expires_at)<=Date.now())throw Error('Invitation unavailable');if(!['Accepted','Declined'].includes(args.decision))throw Error('Invalid decision');if(args.decision==='Accepted'&&!db.links.some(l=>l.profile===r.profile&&l.user===member.user&&['Active','Pending'].includes(l.status)))db.links.push({name:id('link'),profile:r.profile,user:member.user,kind:'Teacher membership',status:'Pending'});r.status=args.decision;return result({status:r.status})
  }
  if(method==='request_by_email'){const p=db.profiles.find(p=>p.kind==='Institute'&&p.status==='Verified'&&p.user===String(args.email).trim().toLowerCase());if(p&&!db.links.some(l=>l.profile===p.name&&l.user===member.user&&['Pending','Active'].includes(l.status)))db.links.push({name:id('link'),profile:p.name,user:member.user,kind:'Teacher membership',status:'Pending'});return result({message:'Request saved in preview'})}
 }
 if(module==='teaching'){
  const rooms=db.rooms.filter(r=>r.active!==0&&visible(r)),names=new Set(rooms.map(r=>r.name))
  if(method==='programmes')return (db.programmes||[]).filter(p=>role!=='Teacher'||p.modules.some(m=>m.teacher===member.name))
  if(method==='overview'){const memberships=db.links.filter(l=>l.kind==='Teacher membership'&&['Active','Pending'].includes(l.status)&&(role==='Admin'?l.profile==='teen-academy':l.user===member.user)).map(l=>({...l,person:db.profiles.find(p=>role==='Admin'?p.user===l.user:p.name===l.profile)}));const totals={};for(const i of db.invoices.filter(i=>names.has(i.classroom))){const k=i.currency+i.status;totals[k]??={currency:i.currency,status:i.status,amount:0};totals[k].amount+=i.amount}return {students:new Set((db.enrollments||[]).filter(e=>names.has(e.classroom)&&e.active).map(e=>e.student)).size,teachers:memberships.filter(l=>l.status==='Active').length,classrooms:rooms.map(roomView),totals:Object.values(totals),memberships,programmes:await previewRequest('teaching','programmes')}}
  if(method==='membership'){const l=find(db.links,args.name);if(l.kind!=='Teacher membership'||(args.status==='Left'?l.user!==member.user:role!=='Admin'))throw Error('Membership permission required');if(!['Active','Rejected','Removed','Left'].includes(args.status))throw Error('Invalid decision');l.status=args.status;if(['Removed','Left'].includes(l.status)){const t=(db.teachers||[]).find(t=>t.user===l.user);db.rooms.filter(r=>r.owner_type!=='Teacher'&&r.public_provider===l.profile&&r.teacher===t?.name).forEach(r=>r.teacher_assignment_active=0)}return result({status:l.status})}
  if(method==='leave_class'){const r=find(db.rooms,args.classroom);if(role!=='Teacher'||r.teacher!==member.name||r.owner_type==='Teacher')throw Error('Only assigned institute teachers can leave');r.teacher_assignment_active=0;return result({left:true})}
  if(method==='save_programme'){if(role!=='Admin')throw Error('Institute admin required');if(!v.title||!v.modules?.length||new Set(v.modules.map(m=>m.classroom)).size!==v.modules.length)throw Error('Choose distinct modules and a title');const p={...v,name:id('programme'),currency:'LKR',active:1,students:0};for(const m of p.modules){const r=find(db.rooms,m.classroom);if(r.owner_type==='Teacher'||r.programme||(db.enrollments||[]).some(e=>e.classroom===r.name))throw Error('Choose an unbundled, unenrolled institute classroom');Object.assign(m,{title:r.subject,teacher:r.teacher,teacher_name:r.teacher_name})}for(const m of p.modules)Object.assign(find(db.rooms,m.classroom),{programme:p.name,billing_type:'Programme module'});(db.programmes||=[]).push(p);return result(p.name)}
  if(method==='enroll_programme'){if(role!=='Student')throw Error('Student required');const p=find(db.programmes||[],args.programme);if(db.invoices.some(i=>i.student===member.name&&i.programme===p.name))return {existing:true};for(const m of p.modules)(db.enrollments||=[]).push({name:id('enrollment'),student:member.name,classroom:m.classroom,active:1,access_override:'Automatic'});db.invoices.push({name:id('invoice'),programme:p.name,classroom:p.modules[0].classroom,student:member.name,amount:p.fee,currency:'LKR',status:'Unpaid',recipient:'Teen Academy',beneficiary:'Institute',due_date:new Date().toISOString().slice(0,10)});return result({existing:false})}
  if(method==='month_invoice'){const r=find(db.rooms,args.classroom);if(role!=='Student'||!visible(r)||r.billing_type!=='Monthly'||!/^\d{4}-(0[1-9]|1[0-2])$/.test(args.month))throw Error('Choose an enrolled monthly class and valid month');const old=db.invoices.find(i=>i.student===member.name&&i.classroom===r.name&&i.billing_month===args.month);if(old)return {invoice:old.name,existing:true};const invoice={name:id('invoice'),classroom:r.name,student:member.name,amount:r.fee_mode==='Free'?0:r.fee,currency:'LKR',status:'Unpaid',billing_month:args.month,due_date:args.month+'-01',recipient:r.owner_type==='Teacher'?r.teacher_name:'Teen Academy',beneficiary:r.owner_type};db.invoices.push(invoice);return result({invoice:invoice.name,existing:false})}
 }
 if(module==='portal_session')return method==='current'?{authenticated:true,role:role==='Super Admin'?role:member.role,member:role==='Super Admin'?null:member,user:member.user}:{students:0,teachers:db.profiles.filter(p=>p.kind==='Teacher').length,institutes:db.profiles.filter(p=>p.kind==='Institute').length,pending_profiles:db.profiles.filter(p=>p.status==='Pending').length,pending_payouts:0}
 if(module==='portal_policy'){
  if(method==='public')return {...(db.policy||{privacy_policy_url:'',privacy_policy_version:'',provider_applications_enabled:false}),google_available:false}
  if(method==='save'){if(role!=='Super Admin')throw Error('Owner access required');if(args.privacy_policy_url&&!/^https:\/\//.test(args.privacy_policy_url))throw Error('Use an HTTPS policy URL');if(args.provider_applications_enabled&&(!args.privacy_policy_url||!args.privacy_policy_version))throw Error('Add a policy URL and version before enabling applications');db.policy=args;return result({...args,google_available:false})}
  throw Error('Google sign-in requires a configured Frappe site. No real account is created in preview.')
 }
 if(module==='registration'){
  if(method==='applications')return []
  throw Error('Applications and verification emails require a connected Frappe site. This preview does not send emails.')
 }
 if(module==='catalog'){
  if(method==='publishing_options')return db.profiles.filter(p=>p.status==='Verified'&&(p.user===member.user||db.links.some(l=>l.profile===p.name&&l.user===member.user&&l.kind==='Teacher membership'&&l.status==='Active')))
  if(method==='detail'){const p=find(db.profiles,args.profile);return {profile:p,classes:db.rooms.filter(r=>r.active!==0&&r.published&&(r.public_provider===p.name||p.kind==='Teacher'&&r.teacher===(db.teachers||[roles.Teacher]).find(t=>t.user===p.user)?.name)),teachers:db.profiles.filter(t=>t.kind==='Teacher'&&t.status==='Verified'&&db.links.some(l=>l.profile===p.name&&l.user===t.user&&l.kind==='Teacher membership'&&l.status==='Active'))}}
  if(method==='join_class'){if(role!=='Student')throw Error('Student required');const r=find(db.rooms,args.classroom);if(r.programme)throw Error('Join the complete programme from Programmes');if((db.enrollments||[]).some(e=>e.student===member.name&&e.classroom===r.name))return {existing:true};(db.enrollments||=[]).push({name:id('enrollment'),student:member.name,classroom:r.name,active:1,access_override:'Automatic'});if(r.billing_type==='Monthly')await previewRequest('teaching','month_invoice',{classroom:r.name,month:new Date().toISOString().slice(0,7)});return result({existing:false})}
 }
 if(module==='api'){
  if(method==='bootstrap')return {institute:db.institute,member,mode:'interface-preview',lms_base:'/lms',username:member.user}
  if(method==='dashboard_summary'){const invoices=db.invoices.filter(i=>role==='Student'?i.student===member.name:db.rooms.some(r=>r.name===i.classroom&&visible(r)));return {...blankMoney,classrooms:db.rooms.filter(r=>r.active!==0&&visible(r)).length,paid_count:invoices.filter(i=>i.status==='Paid').length,paid_total:invoices.filter(i=>i.status==='Paid').reduce((a,i)=>a+i.amount,0)}}
  if(method==='classrooms'){if(Number(args.deleted)&&!['Teacher','Admin'].includes(role))throw Error('Classroom unavailable');return db.rooms.filter(r=>(Number(args.deleted)?r.active===0:r.active!==0)&&visible(r)&&(!args.search||r.title.toLowerCase().includes(args.search.toLowerCase()))).slice((Number(args.page)||0)*24,((Number(args.page)||0)+1)*24).map(roomView)}
  if(method==='set_classroom_deleted'){const room=find(db.rooms,args.name);if(!rights(room).delete)throw Error('Your classroom permission does not allow deletion');if(![0,1].includes(args.deleted))throw Error('Invalid classroom state');room.active=1-args.deleted;return result({name:room.name,active:room.active})}
  if(method==='schedule')return db.sessions.filter(s=>db.rooms.some(r=>r.name===s.classroom&&r.active!==0&&visible(r)))
  if(method==='invoices')return db.invoices.filter(i=>role==='Student'?i.student===member.name:db.rooms.some(r=>r.name===i.classroom&&visible(r))).slice((Number(args.page)||0)*50,((Number(args.page)||0)+1)*50)
  if(['news','notifications'].includes(method))return db[method]
  if(method==='members')return [...(db.students||[]),...(db.teachers||[])]
  if(method==='teachers')return role==='Teacher'?[member]:(db.teachers||[roles.Teacher]).filter(t=>!db.scenario||db.links.some(l=>l.kind==='Teacher membership'&&l.user===t.user&&l.status==='Active'))
  if(method==='save_classroom'){
   const previous=db.rooms.find(r=>r.name===v.name),room={...v,name:previous?.name||id('class'),institute:db.institute.name,teacher:v.teacher||roles.Teacher.name,teacher_name:(db.teachers||[]).find(t=>t.name===(v.teacher||roles.Teacher.name))?.full_name||'Teacher preview',owner_type:previous?.owner_type||(role==='Teacher'?'Teacher':'Institute'),owner_user:previous?.owner_user||member.user,teacher_access:v.teacher_access||(role==='Teacher'?'Full control':'Teaching only'),teacher_assignment_active:1,fee:Number(v.fee)||0,active:1,students:0,access:{allowed:true,reason:'Interface preview'},font:v.font||'default'}
   if(previous&&!rights(previous).edit)throw Error('Full control required');if(!['Teacher','Admin'].includes(role))throw Error('Teacher or institute admin required');if(role==='Teacher'){room.teacher=member.name;room.owner_type=previous?.owner_type||'Teacher'}
   if(previous)Object.assign(previous,room);else db.rooms.push(room);return result(room.name)
  }
  if(method==='classroom_detail'){const room=find(db.rooms,args.name);if(role==='Student'&&room.active===0)throw Error('Classroom unavailable');const shown=roomView(room);return {room:shown,access:shown.access,sessions:shown.access.allowed?db.sessions.filter(s=>s.classroom===room.name):[],materials:[],feedback:[],announcements:[]}}
  if(method==='save_session'){const old=db.sessions.find(s=>s.name===v.name),row={...v,name:old?.name||id('session'),status:v.status||'Scheduled'};if(old)Object.assign(old,row);else db.sessions.push(row);return result(row.name)}
  if(method==='enrollments')return (db.enrollments||[]).filter(e=>e.classroom===args.classroom).slice(0,100)
  if(method==='save_branding'){Object.assign(db.institute,v);return result({institute:db.institute,member})}
  if(method==='notification_preferences')return result({saved:true})
  if(method==='save_news'){db.news.push({...v,name:id('news'),creation:new Date().toISOString()});return result({saved:true})}
  if(method==='video_courses')return {courses:[],completions:[]}
 }
 if(module==='profiles'){
  if(method==='me')return {profile:db.profiles.find(p=>p.user===member.user)||null,phone_verified:true}
  if(method==='save_profile'){
   v.socials=providerSocials(v.kind,v.socials)
   if(db.profiles.some(p=>p.username===v.username&&p.user!==member.user))throw Error('That username is already used in this preview.')
   let p=db.profiles.find(p=>p.user===member.user);if(!p){p={name:id('profile'),user:member.user};db.profiles.push(p)}Object.assign(p,v,{status:v.kind==='Student'||p.display_name===v.display_name?'Verified':'Pending'});return result(p)
  }
  if(method==='pending')return db.profiles.filter(p=>p.status==='Pending')
  if(method==='search')return db.profiles.filter(p=>p.status==='Verified'&&p.kind!=='Student'&&(p.username+' '+p.display_name).toLowerCase().includes((args.query||'').toLowerCase().replace(/^@/,'')))
  if(method==='review'){const p=find(db.profiles,args.profile);p.status=args.decision;if(args.decision==='Verified')p.code='PREVIEW-'+p.name.slice(-4);return result(p)}
  if(method==='relationships')return {followers:db.links.filter(l=>l.profile===args.profile&&l.kind==='Follow'&&l.status==='Active').length,owns_profile:find(db.profiles,args.profile).user===member.user,relationships:db.links.filter(l=>l.profile===args.profile)}
  if(method==='relate'){const row={name:id('link'),profile:args.profile,user:member.user,kind:args.kind,status:args.kind==='Follow'?'Active':'Pending'};db.links.push(row);return result(row)}
  if(method==='change_relationship'){if(find(db.links,args.relationship).kind==='Teacher membership')return previewRequest('teaching','membership',{name:args.relationship,status:args.status});Object.assign(find(db.links,args.relationship),{status:args.status});return result({saved:true})}
  if(method==='followed_updates')return []
  if(method==='publish_update')return result({saved:true})
 }
 if(module==='owner_pricing'){
  if(method==='entitlements')return {'Study Space':true,'AI Papers':false,'To-do':false,Journal:false}
  if(method==='assignments')return db.assignments.filter(a=>a.active)
  if(method==='assign'){
   if(role!=='Super Admin')throw Error('Use the Super Admin preview to assign prices.')
   for(const a of db.assignments)if(a.customer===v.customer&&a.product===v.product)a.active=0
   const row={...v,name:id('price'),active:1};db.assignments.push(row);return result(row)
  }
  if(method==='quote'){
   const a=db.assignments.find(a=>a.active&&a.customer===member.user&&a.product===args.product)
   if(!a)throw Error('No price is assigned. In Super Admin → Pricing, use '+member.user+' to try an assignment.')
   const subtotal=Number(a.base_minor)+Math.max(0,1-Number(a.included_units))*Number(a.unit_minor),discount=Math.floor((subtotal*Number(a.discount_bps)+5000)/10000),tax=Math.floor(((subtotal-discount)*Number(a.tax_bps)+5000)/10000)
   return {name:id('quote'),product:a.product,currency:a.currency,period:a.period,expires_at:new Date(Date.now()+900000).toISOString(),breakdown:{subtotal_minor:subtotal,discount_minor:discount,tax_minor:tax,total_minor:subtotal-discount+tax},payment_available:false}
  }
  if(method==='classroom_price'){find(db.rooms,args.classroom).fee=Number(args.amount_minor)/100;return result({saved:true})}
  if(method==='grant'){db.grants.push({...args,name:id('grant')});return result({saved:true})}
 }
 if(module==='papers'){
  if(method==='listing')return db.papers.filter(p=>member.role!=='Student'||p.status==='Published')
  if(method==='detail')return find(db.papers,args.name)
  if(method==='draft'){
   if(!v.classroom||!v.title?.trim()||!v.questions?.length)throw Error('Create a classroom, title and questions first.')
   if(v.questions.some(q=>!q.prompt?.trim()||q.kind==='MCQ'&&q.options.some(o=>!o.trim())))throw Error('Fill in each question and its options.')
   const old=db.papers.find(p=>p.name===v.name),p={...v,name:old?.name||id('paper'),source:old?.source||'Manual',status:'Draft',max_marks:v.questions.reduce((s,q)=>s+Number(q.marks),0)}
   if(old)Object.assign(old,p);else db.papers.push(p);return result(p)
  }
  if(method==='publish'){find(db.papers,args.name).status='Published';return result({status:'Published'})}
  if(method==='archive'){find(db.papers,args.name).status='Archived';return result({status:'Archived'})}
  if(method==='submissions')return db.attempts.filter(a=>a.paper===args.paper)
  if(method==='start'){
   const p=find(db.papers,args.name);let a=db.attempts.find(a=>a.paper===p.name);if(!a){a={name:id('attempt'),paper:p.name,student:member.name,status:'Started',started_at:new Date().toISOString(),deadline:new Date(Date.now()+p.duration_minutes*60000).toISOString()};db.attempts.push(a)}
   if(a.status!=='Started')throw Error('This attempt has been submitted.')
   return result({attempt:a.name,deadline:a.deadline,server_time:new Date().toISOString(),questions:p.questions.map(q=>({...q,options:q.kind==='True/False'?['True','False']:q.options,answer:undefined}))})
  }
  if(method==='submit'){const a=find(db.attempts,args.attempt),p=find(db.papers,a.paper);a.answers=JSON.stringify(args.answers);a.score=p.questions.reduce((s,q,i)=>s+(q.kind!=='Written'&&Number(q.answer)===args.answers[i]?Number(q.marks):0),0);a.status=p.questions.some(q=>q.kind==='Written')?'Submitted':'Graded';return result({status:a.status,score:a.score})}
  if(method==='mark'){Object.assign(find(db.attempts,args.attempt),{score:args.score,feedback:args.feedback,status:'Graded'});return result({saved:true})}
  if(method==='generate')throw Error('AI generation requires the real server, an active entitlement and OpenAI configuration. This preview does not send prompts or spend API credits.')
 }
 if(module==='wallet'){
  if(method==='admin_queue')return {requests:[],methods:[]}
  if(method==='dashboard')return {wallet:{name:'preview-wallet',currency:'USD',country:'International',beneficiary:role==='Admin'?'Institute':'Teacher',available_minor:0,held_minor:0},minimum_minor:2000,methods:[],requests:[],ledger:[]}
 }
 if(module==='operations'){
  if(method==='attendance')return db.attendance
  if(method==='tickets')return db.tickets
  if(method==='thread')return db.replies.filter(r=>r.ticket===args.ticket)
  if(method==='create_ticket'){const t={...args,name:id('ticket'),requester:member.user,status:'Open'};db.tickets.push(t);db.replies.push({ticket:t.name,author_user:member.user,body:args.body,creation:new Date().toISOString()});return result(t)}
  if(method==='reply'){db.replies.push({...args,author_user:member.user,creation:new Date().toISOString()});if(args.status)find(db.tickets,args.ticket).status=args.status;return result({saved:true})}
 }
 if(module==='soul'&&method==='status')return {configured:false,enabled:false,available:false}
 if(['account','contact','calendar_sync','youtube'].includes(module))throw Error('This connected service requires a configured Frappe site. You can explore its controls here without sending data.')
 throw Error('This action needs the connected backend. Preview navigation does not send messages, collect payments or change real accounts.')
}
