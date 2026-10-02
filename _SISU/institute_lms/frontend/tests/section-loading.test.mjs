import test from 'node:test'
import assert from 'node:assert/strict'
import {loadSections} from '../src/lib/section-loading.js'

test('one failed request leaves other connected sections available',async()=>{
  const result=await loadSections(['courses','applications','classes'],path=>{
    if(path==='applications')return Promise.reject(new Error('Permission denied.'))
    return Promise.resolve([{id:path}])
  })

  assert.deepEqual(result.values,{courses:[{id:'courses'}],classes:[{id:'classes'}]})
  assert.deepEqual(result.errors,{applications:'Permission denied.'})
  assert.equal(result.authError,undefined)
})

test('an expired session is still reported as an authentication failure',async()=>{
  const expired=new Error('Sign-in session expired')
  expired.status=401
  const result=await loadSections(['courses'],()=>Promise.reject(expired))

  assert.equal(result.authError,expired)
})

test('forbidden and unavailable sections show actionable status messages',async()=>{
  const forbidden=Object.assign(new Error('Permission denied'),{status:403})
  const unavailable=Object.assign(new Error('Service unavailable'),{status:503})
  const result=await loadSections(['profiles/unassigned','admin/overview'],path=>
    Promise.reject(path==='profiles/unassigned'?forbidden:unavailable))

  assert.equal(result.errors['profiles/unassigned'],'Your account is not permitted to view this section.')
  assert.equal(result.errors['admin/overview'],'The server or Supabase is unavailable. Try again shortly.')
})
