import test from 'node:test'
import assert from 'node:assert/strict'
import {loadSections,mergeSectionResults} from '../src/lib/section-loading.js'
import {safeApiErrorMessage} from '../src/lib/api-errors.js'

test('one failed request leaves other connected sections available',async()=>{
  const result=await loadSections(['courses','applications','classes'],path=>{
    if(path==='applications')return Promise.reject(new Error('Permission denied.'))
    return Promise.resolve([{id:path}])
  })

  assert.deepEqual(result.values,{courses:[{id:'courses'}],classes:[{id:'classes'}]})
  assert.deepEqual(result.errors,{applications:'This section could not load. Please try again.'})
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

  assert.equal(result.errors['profiles/unassigned'],safeApiErrorMessage(403))
  assert.equal(result.errors['admin/overview'],safeApiErrorMessage(503))
})

test('refreshing one failed section preserves its prior data and successful sections',async()=>{
  const previousValues={
    institutions:[{id:'old',title:'Old institution'}],
    applications:[{id:'application'}],
    'admin/overview':{institutions:1},
  }
  const result=await loadSections(['institutions','applications'],path=>{
    if(path==='institutions')return Promise.reject(Object.assign(new Error('unsafe detail'),{status:503}))
    return Promise.resolve([{id:'fresh'}])
  })
  const merged=mergeSectionResults(previousValues,{},['institutions','applications'],result)

  assert.deepEqual(merged.values.institutions,previousValues.institutions)
  assert.deepEqual(merged.values.applications,[{id:'fresh'}])
  assert.deepEqual(merged.values['admin/overview'],previousValues['admin/overview'])
  assert.equal(merged.errors.institutions,safeApiErrorMessage(503))
})

test('API status messages are safe and stable for expected failures',()=>{
  assert.equal(safeApiErrorMessage(401),'Your session has expired. Please sign in again.')
  assert.equal(safeApiErrorMessage(403),'You do not have permission to complete this request.')
  assert.equal(safeApiErrorMessage(422),'Some information is invalid. Check the form and try again.')
  assert.equal(safeApiErrorMessage(503),'The service is temporarily unavailable. Try again shortly.')
})
