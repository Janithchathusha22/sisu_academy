import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {applicationRole,applicationRoleLabel,workspaceKind,canOpenWorkspacePage} from '../src/lib/workspace.js'

const active=(application_role,institution_id=null)=>({account_status:'active',application_role,institution_id})

test('verified platform and institute administrators get their own workspace',()=>{
  assert.equal(workspaceKind(active('super_admin')),'platform-admin')
  assert.equal(workspaceKind(active('institute_admin','school-a')),'institute-admin')
  assert.equal(canOpenWorkspacePage(active('super_admin'),'approvals'),true)
  assert.equal(canOpenWorkspacePage(active('institute_admin','school-a'),'management'),true)
})

test('verified student profile uses the backend-resolved super admin workspace and label',()=>{
  const owner={profile_kind:'student',account_status:'active',application_role:'super_admin'}
  assert.equal(applicationRole(owner),'super_admin')
  assert.equal(applicationRoleLabel(owner),'Platform administrator')
  assert.equal(workspaceKind(owner),'platform-admin')
  assert.equal(canOpenWorkspacePage(owner,'approvals'),true)
})

test('profile kind and legacy role cannot grant the admin workspace',()=>{
  const ungranted={profile_kind:'super_admin',role:'super_admin',account_status:'active',application_role:'student'}
  assert.equal(applicationRole(ungranted),'student')
  assert.equal(workspaceKind(ungranted),'member')
  assert.equal(canOpenWorkspacePage(ungranted,'approvals'),false)
})

test('students and unapproved users cannot open admin pages',()=>{
  const pending={account_status:'pending',application_role:'super_admin'}
  assert.equal(applicationRole(pending),null)
  assert.equal(applicationRoleLabel(pending),'Applicant')
  for(const profile of [active('student'),pending]){
    assert.equal(canOpenWorkspacePage(profile,'approvals'),false)
    assert.equal(canOpenWorkspacePage(profile,'management'),false)
  }
  assert.equal(workspaceKind(active('institute_admin')),'member')
})

test('admin selection never supplies the application role',async()=>{
  const source=await readFile(new URL('../src/native/PortalRoot.vue',import.meta.url),'utf8')
  assert.match(source,/name:'Admin'/)
  assert.match(source,/await signIn\(email\.value\.trim\(\),password\.value\);await accept\(await currentSession\(\)\)/)
  assert.doesNotMatch(source,/selected\.value.*(role|permission|platform_roles)/)
})

test('Student and Teacher retain signup links and their selected registration type',async()=>{
  const root=await readFile(new URL('../src/native/PortalRoot.vue',import.meta.url),'utf8')
  const registration=await readFile(new URL('../src/native/RegistrationFlow.vue',import.meta.url),'utf8')
  const supabase=await readFile(new URL('../src/lib/supabase.js',import.meta.url),'utf8')
  assert.match(root,/<template v-else><button class="entry-secondary" @click="signup=true">Create \{\{selected\}\} account/)
  assert.match(root,/:initial-type="selected==='Teacher'\?'teacher':'student'"/)
  assert.match(registration,/const type=ref\(props\.initialType==='teacher'\?'teacher':'student'\)/)
  assert.match(registration,/accountType:type\.value/)
  assert.match(registration,/type\.value==='student'&&data\.session/)
  assert.match(supabase,/auth\.signUp\(/)
  assert.match(supabase,/account_type:\s*accountType/)
})
