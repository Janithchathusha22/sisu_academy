<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import Icon from '../Icon.vue'
import Art from '../Art.vue'
import {api,currentSession,logoutSession} from '../lib/api'
import {applicationRole,applicationRoleLabel,canOpenWorkspacePage,workspaceKind} from '../lib/workspace'
import {loadSections} from '../lib/section-loading'

const props=defineProps({session:{type:Object,required:true}})
const emit=defineEmits(['logout','session'])
const page=ref('dashboard'),mobile=ref(false),busy=ref(false),loaded=ref(false),error=ref(''),message=ref('')
const loadErrors=ref({}),learningError=ref(''),learningBusy=ref(false)
const data=ref({}),profile=ref({...props.session.profile}),fullName=ref(profile.value.full_name)
const role=computed(()=>applicationRole(profile.value))
const manager=computed(()=>['teacher','institute_admin','super_admin'].includes(role.value))
const admin=computed(()=>['institute_admin','super_admin'].includes(role.value))
const owner=computed(()=>role.value==='super_admin')
const workspace=computed(()=>workspaceKind(profile.value))
const active=computed(()=>profile.value.account_status==='active')
const roleLabel=computed(()=>applicationRoleLabel(profile.value))
const sidebarLabel=computed(()=>owner.value?'PLATFORM ADMINISTRATION':workspace.value==='institute-admin'?'INSTITUTE ADMINISTRATION':role.value==='teacher'?'YOUR TEACHING SPACE':'YOUR LEARNING SPACE')
const nav=computed(()=>owner.value?[
  ['dashboard','LayoutDashboard','Overview'],['institutions','Landmark','Institutions'],['approvals','Users','People & approvals'],
  ['profile','IdCard','My profile']]:[
  ['dashboard','LayoutDashboard','Overview'],['classes','BookOpen','Classrooms'],['courses','GraduationCap','Courses'],['learning','BookOpen','Lessons'],
  ['schedule','CalendarDays','Schedule'],['attendance','ClipboardCheck','Attendance'],['assignments','NotebookPen','Assignments'],
  ['materials','BookOpen','Materials'],['exams','GraduationCap','Exams'],['results','Award','Results'],
  ['payments','CreditCard','Payments'],['notifications','Bell','Updates'],
  ...(workspace.value==='institute-admin'?[['management','Users','Institute management']]:[]),
  ['profile','IdCard','My profile']].filter(item=>canOpenWorkspacePage(profile.value,item[0])))
const title=computed(()=>nav.value.find(n=>n[0]===page.value)?.[2]||'Workspace')
const rows=computed(()=>data.value[page.value]||[])
const stats=computed(()=>[['Classrooms',data.value.classes?.length],['Courses',data.value.courses?.length],['Attendance records',data.value.attendance?.length]])
const institution=ref(profile.value.institution_id||'')
const course=ref({title:'',description:''})
const classroom=ref({title:'',subject:'',course_id:'',teacher_id:''})
const enrollment=ref({class_id:'',student_id:''})
const register=ref({class_session_id:'',student_id:'',status:'present',note:''})
const meeting=ref({class_id:'',title:'',starts_at:'',ends_at:''})
const newInstitution=ref({title:'',code:''})
const selectedInstitutions=ref({})
const selectedCourse=ref(''),selectedModule=ref(''),modules=ref([]),lessons=ref([])
const adminOverview=ref(null),adminOverviewError=ref('')
const availableCourses=computed(()=>(data.value.courses||[]).filter(r=>r.institution_id===institution.value))
const availableTeachers=computed(()=>(data.value.teachers||[]).filter(r=>r.institution_id===institution.value))
const institutionClasses=computed(()=>(data.value.classes||[]).filter(r=>r.institution_id===institution.value))
const institutionStudents=computed(()=>(data.value.students||[]).filter(r=>r.institution_id===institution.value))
const registerStudents=computed(()=>{
  const selectedSession=(data.value.schedule||[]).find(s=>s.id===register.value.class_session_id)
  const allowed=new Set((data.value.enrollments||[]).filter(e=>e.class_id===selectedSession?.class_id&&e.status==='active').map(e=>e.student_membership_id))
  return (data.value.students||[]).filter(s=>allowed.has(s.id))
})
function navigate(id){if(!canOpenWorkspacePage(profile.value,id))return;page.value=id;mobile.value=false;message.value=''}
function className(id){return data.value.classes?.find(c=>c.id===id)?.title||id}
function studentName(id){return data.value.students?.find(s=>s.id===id)?.student_code||id}
function date(value){return value?new Date(value).toLocaleString():'Not scheduled'}
async function load(){
  busy.value=true;error.value='';loaded.value=false
  try{
    const fresh=await currentSession();profile.value=fresh.profile;emit('session',fresh)
    if(!canOpenWorkspacePage(profile.value,page.value))page.value='dashboard'
    if(workspace.value==='institute-admin')institution.value=profile.value.institution_id
    if(!active.value){data.value={};loaded.value=true;return}
    const paths=owner.value
      ? ['admin/overview','institutions','applications','profiles/unassigned']
      : ['courses','classes','schedule','attendance','enrollments','assignments','materials','exams','results','payments','notifications']
    if(!owner.value&&manager.value)paths.push('students','teachers')
    if(!owner.value&&admin.value)paths.push('institutions')
    const {values,errors,authError}=await loadSections(paths,path=>api('/api/'+path))
    if(authError)throw authError
    data.value=Object.fromEntries(paths.map(path=>[path,path in values?values[path]:[]]));loadErrors.value=errors;loaded.value=true
    adminOverview.value=values['admin/overview']||null
    adminOverviewError.value=errors['admin/overview']||''
    if(owner.value){
      selectedInstitutions.value={}
      for(const row of data.value.applications||[])if(data.value.institutions?.length)selectedInstitutions.value[row.id]=data.value.institutions[0].id
      for(const row of data.value['profiles/unassigned']||[])if(data.value.institutions?.length)selectedInstitutions.value[row.id]=data.value.institutions[0].id
    }
    if(!selectedCourse.value&&data.value.courses?.length)selectedCourse.value=data.value.courses[0].id
  }catch(e){data.value={};error.value=e.message}finally{busy.value=false}
}
async function loadModules(){
  selectedModule.value='';modules.value=[];lessons.value=[];learningError.value=''
  if(!selectedCourse.value)return
  learningBusy.value=true
  try{modules.value=await api('/api/v2/modules?course_id='+encodeURIComponent(selectedCourse.value));if(modules.value.length)selectedModule.value=modules.value[0].id}
  catch(e){learningError.value=e.message}finally{learningBusy.value=false}
}
async function loadLessons(){
  lessons.value=[];learningError.value=''
  if(!selectedModule.value)return
  learningBusy.value=true
  try{lessons.value=await api('/api/v2/lessons?module_id='+encodeURIComponent(selectedModule.value))}
  catch(e){learningError.value=e.message}finally{learningBusy.value=false}
}
async function save(path,body,method='POST'){
  if(busy.value)return false
  busy.value=true;error.value='';message.value=''
  try{await api('/api/'+path,{method,body});message.value='Saved successfully.';await load();return true}
  catch(e){error.value=e.message;return false}finally{busy.value=false}
}
async function createCourse(){if(await save('courses',{...course.value,institution_id:institution.value}))course.value={title:'',description:''}}
async function createInstitution(){if(await save('institutions',newInstitution.value))newInstitution.value={title:'',code:''}}
async function createClass(){if(await save('classes',{...classroom.value,institution_id:institution.value,course_id:classroom.value.course_id||null,teacher_id:classroom.value.teacher_id||null}))classroom.value={title:'',subject:'',course_id:'',teacher_id:''}}
async function record(){await save('attendance',register.value)}
async function schedule(){await save('schedule',{...meeting.value,starts_at:new Date(meeting.value.starts_at).toISOString(),ends_at:new Date(meeting.value.ends_at).toISOString()})}
async function review(row,decision){await save('applications/'+row.id+'/review',{decision,institution_id:selectedInstitutions.value[row.id]||null})}
async function saveProfile(){if(await save('me',{full_name:fullName.value.trim()},'PUT'))fullName.value=profile.value.full_name}
async function logout(){if(busy.value)return;busy.value=true;try{await logoutSession();emit('logout')}catch(e){error.value=e.message}finally{busy.value=false}}
watch(()=>props.session.profile,value=>{profile.value={...value};fullName.value=profile.value.full_name})
watch(selectedCourse,loadModules)
watch(selectedModule,loadLessons)
onMounted(load)
</script>

<template>
  <div class="app-shell connected-campus">
    <button v-if="mobile" class="sidebar-overlay" aria-label="Close navigation" @click="mobile=false"></button>
    <aside class="sidebar" :class="{expanded:mobile}">
      <div class="wordmark"><span class="brand-symbol">s</span>sisu<span class="brand-dot">.</span></div>
      <p class="nav-label">{{sidebarLabel}}</p>
      <nav aria-label="Workspace"><button v-for="item in nav" :key="item[0]" :class="{active:page===item[0]}" :aria-current="page===item[0]?'page':undefined" @click="navigate(item[0])"><Icon :name="item[1]" :size="19"/>{{item[2]}}</button></nav>
      <div class="connection-label"><Icon name="ShieldCheck" :size="16"/>Supabase workspace</div>
    </aside>
    <div class="workspace">
      <header class="topbar"><button class="mobile-menu" aria-label="Open navigation" @click="mobile=true"><Icon name="Menu"/></button><div class="breadcrumb">Your campus / <strong>{{title}}</strong></div><div class="top-actions"><span>{{roleLabel}}</span><button class="button subtle" :disabled="busy" @click="logout">Sign out</button></div></header>
      <main id="main-content" :aria-busy="busy">
        <div class="page-heading"><div><span class="eyebrow">YOUR EVERYDAY, A LITTLE BRIGHTER</span><h1>{{page==='dashboard'?'Hello, '+(profile.full_name||'there'):title}} <span class="greeting-spark">✺</span></h1><p>Your classes. Your people. Your own pace.</p></div><button class="button subtle" :disabled="busy" @click="load">{{busy?'Loading…':'Refresh'}}</button></div>
        <p v-if="error" class="connection-error" role="alert">{{error}} <button :disabled="busy" @click="load">Retry</button></p>
        <p v-if="Object.keys(loadErrors).length" class="connection-note" role="status">Some sections could not load: {{Object.keys(loadErrors).join(', ')}}. The available sections remain usable. <button :disabled="busy" @click="load">Retry</button></p>
        <p v-if="loadErrors[page]" class="connection-error" role="alert">{{loadErrors[page]}}</p>
        <p v-if="message" class="connection-success" role="status">{{message}}</p>
        <section v-if="page==='profile'" class="panel"><h2>Your account</h2><p>{{session.user.email}} · {{roleLabel}} · {{profile.account_status}}</p><form @submit.prevent="saveProfile"><label>Full name<input v-model="fullName" required maxlength="120"></label><button class="button primary" :disabled="busy||!fullName?.trim()">Save profile</button></form><p>Roles and institution membership can only be changed by an authorized administrator.</p></section>
        <section v-else-if="!active" class="panel"><h2>{{profile.account_status==='pending'?'Awaiting approval':'Account '+profile.account_status}}</h2><p>Your account exists, but access to LMS records is not active. Contact the administrator. Refresh after your application is reviewed.</p></section>
        <template v-else-if="owner">
          <template v-if="page==='dashboard'">
            <section class="panel admin-welcome"><span class="eyebrow">CONNECTED PLATFORM CONTROL</span><h2>Super Admin workspace</h2><p>Manage real SISU institutions, review account applications, and assign verified students. This dashboard uses your authenticated Supabase session.</p></section>
            <section class="panel">
              <h2>Platform overview</h2>
              <p v-if="busy&&!adminOverview" role="status">Loading platform totals…</p>
              <div v-else-if="adminOverview" class="stats-row admin-overview-stats">
                <div class="stat-card"><strong>{{adminOverview.institutions}}</strong><span>Institutions</span></div>
                <div class="stat-card"><strong>{{adminOverview.active_students}}</strong><span>Students</span><small>{{adminOverview.verified_students}} verified</small></div>
                <div class="stat-card"><strong>{{adminOverview.active_teachers}}</strong><span>Teachers</span><small>Active memberships</small></div>
                <div class="stat-card"><strong>{{adminOverview.pending_applications}}</strong><span>Pending applications</span></div>
              </div>
              <div v-if="adminOverviewError" class="connection-error" role="alert">{{adminOverviewError}} <button :disabled="busy" @click="load">Retry</button></div>
            </section>
            <div class="connected-grid admin-shortcuts">
              <section class="panel"><h2>Institutions</h2><p>{{adminOverview?.institutions??'—'}} connected institutions</p><button class="button primary" @click="navigate('institutions')">Manage institutions</button></section>
              <section class="panel"><h2>People &amp; approvals</h2><p>{{adminOverview?.pending_applications??'—'}} provider applications · {{data['profiles/unassigned']?.length??'—'}} students awaiting assignment</p><button class="button primary" @click="navigate('approvals')">Review people</button></section>
            </div>
          </template>
          <template v-else-if="page==='institutions'">
            <form class="panel admin-form" @submit.prevent="createInstitution">
              <h2>Create institution</h2>
              <label>Name<input v-model.trim="newInstitution.title" required maxlength="120"></label>
              <label>Unique code<input v-model.trim="newInstitution.code" required pattern="[A-Z][A-Z0-9]{1,11}" minlength="2" maxlength="12" placeholder="SISU01"></label>
              <button class="button primary" :disabled="busy">Create institution</button>
            </form>
            <section class="panel">
              <h2>Connected institutions</h2>
              <p v-if="busy&&!loaded" role="status">Loading institutions…</p>
              <p v-if="loadErrors.institutions" class="connection-error" role="alert">{{loadErrors.institutions}}</p>
              <article v-for="row in data.institutions||[]" :key="row.id" class="data-row"><h3>{{row.title}}</h3><p>{{row.code}} · {{row.id}}</p></article>
              <p v-if="loaded&&!loadErrors.institutions&&!data.institutions?.length">No institutions have been created yet.</p>
            </section>
          </template>
          <template v-else-if="page==='approvals'">
            <section class="panel">
              <h2>Provider applications</h2>
              <p v-if="busy&&!loaded" role="status">Loading applications…</p>
              <p v-if="loadErrors.applications" class="connection-error" role="alert">{{loadErrors.applications}}</p>
              <article v-for="row in data.applications||[]" :key="row.id" class="data-row">
                <h3>{{row.details?.full_name||row.user_id}} · {{row.account_type}}</h3>
                <p>{{row.details?.organization||row.details?.subject||row.details?.email}}</p>
                <label>Institution<select v-model="selectedInstitutions[row.id]" required><option value="" disabled>Select institution</option><option v-for="item in data.institutions||[]" :key="item.id" :value="item.id">{{item.title}}</option></select></label>
                <div class="actions"><button class="button primary" :disabled="busy||!selectedInstitutions[row.id]" @click="review(row,'approved')">Approve</button><button class="button subtle" :disabled="busy" @click="review(row,'rejected')">Reject</button></div>
              </article>
              <p v-if="loaded&&!loadErrors.applications&&!data.applications?.length">No provider applications are waiting for review.</p>
            </section>
            <section class="panel">
              <h2>Assign verified students</h2>
              <p>Assigning a student creates their institution membership; it does not grant platform administration.</p>
              <p v-if="loadErrors['profiles/unassigned']" class="connection-error" role="alert">{{loadErrors['profiles/unassigned']}} If this is a profile visibility permission error, review the additive student-visibility migration before applying it.</p>
              <article v-for="row in data['profiles/unassigned']||[]" :key="row.id" class="data-row">
                <h3>{{row.full_name||row.email}}</h3><p>{{row.email}}</p>
                <label>Institution<select v-model="selectedInstitutions[row.id]" required><option value="" disabled>Select institution</option><option v-for="item in data.institutions||[]" :key="item.id" :value="item.id">{{item.title}}</option></select></label>
                <button class="button primary" :disabled="busy||!selectedInstitutions[row.id]" @click="save('profiles/'+row.id+'/institution',{institution_id:selectedInstitutions[row.id]})">Assign student</button>
              </article>
              <p v-if="loaded&&!loadErrors['profiles/unassigned']&&!data['profiles/unassigned']?.length">No verified unassigned students.</p>
            </section>
          </template>
        </template>
        <template v-else>
          <p v-if="!profile.institution_id&&!owner" class="connection-note">Your account is active but has no institution assigned yet. An administrator must link your membership before classes become available.</p>
          <label v-if="owner&&['courses','classes'].includes(page)" class="institution-picker">Institution<select v-model="institution"><option value="" disabled>Choose institution</option><option v-for="r in data.institutions" :key="r.id" :value="r.id">{{r.title}}</option></select></label>
          <template v-if="page==='dashboard'">
            <section v-if="owner&&page==='dashboard'" class="panel">
              <h2>Super Admin Overview</h2>
              <p v-if="adminOverviewError" class="connection-error">{{adminOverviewError}}</p>
              <div v-if="adminOverview" class="stats-row">
                <div class="stat-card"><strong>{{adminOverview.institutions}}</strong><span>Institutions</span></div>
                <div class="stat-card"><strong>{{adminOverview.verified_students}}</strong><span>Verified Students</span></div>
                <div class="stat-card"><strong>{{adminOverview.active_students}}</strong><span>Active Students</span></div>
                <div class="stat-card"><strong>{{adminOverview.active_teachers}}</strong><span>Active Teachers</span></div>
                <div class="stat-card"><strong>{{adminOverview.pending_applications}}</strong><span>Pending Applications</span></div>
              </div>
            </section>
            <section v-if="owner" class="panel"><h2>Platform administrator</h2><p>Review provider applications, create institutions, and assign verified students.</p><button class="button primary" @click="navigate('approvals')">Open People & approvals</button><p>{{data.applications?.length||0}} pending provider applications · {{data['profiles/unassigned']?.length||0}} students awaiting assignment</p></section>
            <section v-else-if="workspace==='institute-admin'" class="panel"><h2>Institute administrator</h2><p>Manage classrooms and your institution's teaching records.</p><button class="button primary" @click="navigate('management')">Open institute management</button><p>{{data.students?.length||0}} students · {{data.teachers?.length||0}} teachers</p></section>
            <section v-else-if="role==='teacher'" class="panel"><h2>Teaching workspace</h2><p>Manage your courses, lessons, schedule and attendance for your assigned institution.</p><button class="button primary" @click="navigate('courses')">Open courses</button></section>
            <section v-if="role==='student'" class="hero"><div class="hero-copy"><span class="hero-label">YOUR SPACE TO GROW</span><h2>A little progress.<br>A world of possibility.</h2><p>Your learning and teaching, together in one place.</p><button class="button dark" @click="navigate('classes')">Your classrooms <Icon name="ArrowRight" :size="17"/></button></div><Art/></section>
            <div class="stats-row"><div v-for="stat in stats" :key="stat[0]" class="stat-card"><span class="stat-icon violet"><Icon name="BookOpen"/></span><div><strong>{{loaded?stat[1]:'—'}}</strong><span>{{stat[0]}}</span></div></div></div>
            <div class="connected-grid"><section class="panel"><h2>Coming up</h2><article v-for="r in (data.schedule||[]).filter(s=>new Date(s.ends_at)>new Date()).sort((a,b)=>a.starts_at.localeCompare(b.starts_at)).slice(0,5)" :key="r.id" class="data-row"><h3>{{r.title}}</h3><p>{{className(r.class_id)}} · {{date(r.starts_at)}}</p></article><p v-if="loaded&&!(data.schedule||[]).some(s=>new Date(s.ends_at)>new Date())">No upcoming sessions.</p></section><section class="panel"><h2>Your workspace</h2><p>Use the sidebar for your course, schedule and learning records.</p><p>Lists show up to 200 recent records. Counts describe the loaded records, not institution-wide totals.</p><p>Legacy marketplace, wallet, AI papers and community screens are retained in the separate preview; those integrations are not live in Supabase yet.</p></section></div>
          </template>
          <template v-else-if="page==='learning'">
            <section class="panel"><h2>Courses and lessons</h2><label>Course<select v-model="selectedCourse"><option value="">Choose a course</option><option v-for="r in data.courses||[]" :key="r.id" :value="r.id">{{r.title}}</option></select></label><label v-if="modules.length">Module<select v-model="selectedModule"><option v-for="r in modules" :key="r.id" :value="r.id">{{r.title}}</option></select></label><p v-if="learningBusy">Loading lessons…</p><p v-if="learningError" class="connection-error" role="alert">{{learningError}}</p><p v-if="loaded&&!data.courses?.length">No courses are available for your account.</p><p v-if="selectedCourse&&!modules.length&&!learningBusy&&!learningError">This course has no visible modules yet.</p><article v-for="r in lessons" :key="r.id" class="data-row"><h3>{{r.title}}</h3><p>{{r.description||'No description yet.'}}</p><a v-if="r.video_url" :href="r.video_url" target="_blank" rel="noopener noreferrer">Open video</a></article><p v-if="selectedModule&&!lessons.length&&!learningBusy&&!learningError">No lessons are available in this module yet.</p></section>
          </template>
          <template v-else-if="page==='management'&&workspace==='institute-admin'">
            <section class="panel"><h2>Your institution</h2><article v-for="r in data.institutions||[]" :key="r.id" class="data-row"><h3>{{r.title}}</h3><p>{{r.code}}</p></article><p v-if="loaded&&!data.institutions?.length">No active institution is available.</p></section>
            <div class="connected-grid"><section class="panel"><h2>Students</h2><article v-for="r in data.students||[]" :key="r.id" class="data-row">{{r.display_name||r.student_code||r.id}}</article></section><section class="panel"><h2>Teachers</h2><article v-for="r in data.teachers||[]" :key="r.id" class="data-row">{{r.display_name||r.teacher_code||r.id}}</article></section></div>
          </template>
          <template v-else-if="page==='approvals'&&owner">
            <section class="panel"><h2>Institutions</h2><form @submit.prevent="save('institutions',newInstitution)"><label>Name<input v-model="newInstitution.title" required maxlength="120"></label><label>Unique code<input v-model="newInstitution.code" required pattern="[A-Z][A-Z0-9]{1,11}" minlength="2" maxlength="12" placeholder="SISU01"></label><button class="button primary" :disabled="busy">Create institution</button></form></section>
            <section class="panel"><h2>Provider applications</h2><article v-for="r in data.applications" :key="r.id" class="data-row"><h3>{{r.details.full_name||r.user_id}} · {{r.account_type}}</h3><p>{{r.details.organization||r.details.subject}}</p><label>Institution<select v-model="selectedInstitutions[r.id]"><option v-for="i in data.institutions" :key="i.id" :value="i.id">{{i.title}}</option></select></label><div class="actions"><button class="button primary" :disabled="busy||!selectedInstitutions[r.id]" @click="review(r,'approved')">Approve</button><button class="button subtle" :disabled="busy" @click="review(r,'rejected')">Reject</button></div></article><p v-if="loaded&&!data.applications?.length">No pending applications.</p></section>
            <section class="panel"><h2>Students awaiting institution assignment</h2><article v-for="r in data['profiles/unassigned']" :key="r.id" class="data-row"><h3>{{r.full_name||r.email}}</h3><label>Institution<select v-model="selectedInstitutions[r.id]"><option v-for="i in data.institutions" :key="i.id" :value="i.id">{{i.title}}</option></select></label><button class="button primary" :disabled="busy||!selectedInstitutions[r.id]" @click="save('profiles/'+r.id+'/institution',{institution_id:selectedInstitutions[r.id]})">Assign student</button></article><p v-if="loaded&&!data['profiles/unassigned']?.length">No unassigned students.</p></section>
          </template>
          <template v-else>
            <section class="panel"><h2>{{title}}</h2><p v-if="busy&&!loaded">Loading your records…</p><p v-if="loaded&&!rows.length">No records available for your account.</p>
              <article v-for="r in rows" :key="r.id" class="data-row">
                <h3>{{r.title||r.body||(page==='attendance'?r.status:page==='payments'?r.currency+' '+r.amount:page==='results'?'Score: '+(r.score??'Not graded'):r.id)}}</h3>
                <p v-if="r.class_id">{{className(r.class_id)}}</p><p v-if="r.description||r.instructions">{{r.description||r.instructions}}</p>
                <p v-if="page==='schedule'">{{date(r.starts_at)}} – {{date(r.ends_at)}} · {{r.mode}}</p>
                <p v-if="page==='attendance'">{{studentName(r.student_membership_id)}} · {{date(r.recorded_at)}}</p>
                <p v-if="page==='assignments'">Due: {{date(r.due_at)}}</p><p v-if="page==='exams'">Opens: {{date(r.opens_at)}} · Closes: {{date(r.closes_at)}}</p>
                <p v-if="page==='payments'">{{r.status}} · {{date(r.created_at)}}</p><p v-if="page==='results'">{{r.feedback}}</p>
                <p v-if="page==='materials'">{{r.download_policy}} · File delivery is not enabled in this workspace yet.</p>
                <p v-if="page==='courses'">{{r.published?'Published':'Draft'}}</p>
                <button v-if="page==='courses'&&(admin||(manager&&r.created_by===profile.id))" class="button subtle" :disabled="busy" @click="save('courses/'+r.id,{published:!r.published},'PUT')">{{r.published?'Unpublish':'Publish'}}</button>
                <label v-if="page==='attendance'&&manager">Update status<select :value="r.status" :disabled="busy" @change="save('attendance/'+r.id,{status:$event.target.value},'PUT')"><option v-for="s in ['present','absent','excused']" :key="s" :value="s">{{s}}</option></select></label>
              </article>
            </section>
            <form v-if="page==='courses'&&manager" class="panel" @submit.prevent="createCourse"><h2>Create course</h2><label>Title<input v-model="course.title" required maxlength="120"></label><label>Description<textarea v-model="course.description" maxlength="2000"></textarea></label><button class="button primary" :disabled="busy||!institution">Save course</button></form>
            <div v-if="page==='classes'&&admin" class="connected-grid">
              <form class="panel" @submit.prevent="createClass"><h2>Create classroom</h2><label>Title<input v-model="classroom.title" required maxlength="120"></label><label>Subject<input v-model="classroom.subject" required maxlength="120"></label><label>Course<select v-model="classroom.course_id"><option value="">No course</option><option v-for="r in availableCourses" :key="r.id" :value="r.id">{{r.title}}</option></select></label><label>Teacher<select v-model="classroom.teacher_id"><option value="">Not assigned</option><option v-for="r in availableTeachers" :key="r.id" :value="r.id">{{r.teacher_code||r.id}}</option></select></label><button class="button primary" :disabled="busy||!institution">Save classroom</button></form>
              <form class="panel" @submit.prevent="save('enrollments',{...enrollment,institution_id:institution})"><h2>Enroll student</h2><label>Class<select v-model="enrollment.class_id" required><option v-for="r in institutionClasses" :key="r.id" :value="r.id">{{r.title}}</option></select></label><label>Student<select v-model="enrollment.student_id" required><option v-for="r in institutionStudents" :key="r.id" :value="r.id">{{r.student_code||r.id}}</option></select></label><button class="button primary" :disabled="busy||!institution">Enroll</button></form>
            </div>
            <form v-if="page==='schedule'&&admin" class="panel" @submit.prevent="schedule"><h2>Schedule class</h2><label>Class<select v-model="meeting.class_id" required><option v-for="r in data.classes" :key="r.id" :value="r.id">{{r.title}}</option></select></label><label>Title<input v-model="meeting.title" required maxlength="120"></label><label>Start (your local time)<input v-model="meeting.starts_at" type="datetime-local" required></label><label>End (your local time)<input v-model="meeting.ends_at" type="datetime-local" required></label><button class="button primary" :disabled="busy">Save session</button></form>
            <form v-if="page==='attendance'&&manager" class="panel" @submit.prevent="record"><h2>Record attendance</h2><label>Class session<select v-model="register.class_session_id" required @change="register.student_id=''"><option v-for="r in data.schedule" :key="r.id" :value="r.id">{{r.title}} · {{date(r.starts_at)}}</option></select></label><label>Enrolled student<select v-model="register.student_id" required><option v-for="r in registerStudents" :key="r.id" :value="r.id">{{r.student_code||r.id}}</option></select></label><label>Status<select v-model="register.status"><option v-for="s in ['present','absent','excused']" :key="s" :value="s">{{s}}</option></select></label><label>Note<input v-model="register.note" maxlength="500"></label><button class="button primary" :disabled="busy||!register.student_id">Save attendance</button></form>
          </template>
        </template>
        <footer class="main-footer">A little space. A world of possibility.<span>Authenticated records · No demo data</span></footer>
      </main>
    </div>
  </div>
</template>

<style scoped>
.connected-campus{color:#433552}.sidebar{overflow-y:auto}.sidebar nav{display:grid;gap:3px}.sidebar nav button{min-height:39px}.connection-label{display:flex;gap:8px;font-size:11px;margin:22px 0;color:#706181}.top-actions{display:flex;gap:16px;align-items:center;font-size:12px}.connected-grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}.panel{margin-bottom:22px}.panel h2{font-size:20px;margin-bottom:16px}.panel h3{font-size:15px}.panel p{font-size:13px;line-height:1.7;margin:10px 0}.data-row{padding:17px 0;border-top:1px solid #eae1f3;overflow-wrap:anywhere}.panel label,.institution-picker{display:grid;gap:8px;margin:16px 0;font-size:13px}.panel input,.panel select,.panel textarea,.institution-picker select{width:100%;min-width:0;box-sizing:border-box;padding:13px;border:1px solid #d8c9e7;border-radius:12px;background:#fefbff;color:#433552;font:inherit}.panel input:focus,.panel select:focus,.panel textarea:focus{outline:2px solid #a893e2;outline-offset:2px}.panel form{max-width:650px}.panel .button{margin-top:10px}.actions{display:flex;gap:12px}.connection-error,.connection-success,.connection-note{padding:15px;border-radius:12px;font-size:13px;margin-bottom:20px}.connection-error{background:#fff0f2;color:#872f42;border:1px solid #efbec9}.connection-success{background:#edf9f1;color:#276541}.connection-note{background:#fff7e7;color:#765522}.connection-error button{text-decoration:underline;margin-left:12px}.button:disabled{opacity:.55;cursor:not-allowed}.hero h2{font-size:30px}.hero p{max-width:280px}.hero>svg{pointer-events:none}.stats-row strong{font-variant-numeric:tabular-nums}@media(max-width:760px){.connected-grid{grid-template-columns:1fr}.top-actions>span{display:none}.connected-campus .topbar{justify-content:space-between}.hero h2{font-size:24px}}
</style>
