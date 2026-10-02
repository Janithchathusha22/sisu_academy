import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {workspaceKind,canOpenWorkspacePage} from '../src/lib/workspace.js'

const active=(role,institution_id=null)=>({account_status:'active',role,institution_id})

test('verified platform and institute administrators get their own workspace',()=>{
  assert.equal(workspaceKind(active('super_admin')),'platform-admin')
  assert.equal(workspaceKind(active('institute_admin','school-a')),'institute-admin')
  assert.equal(canOpenWorkspacePage(active('super_admin'),'approvals'),true)
  assert.equal(canOpenWorkspacePage(active('institute_admin','school-a'),'management'),true)
})

test('students and unapproved users cannot open admin pages',()=>{
  for(const profile of [active('student'),{account_status:'pending',role:'super_admin'}]){
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
