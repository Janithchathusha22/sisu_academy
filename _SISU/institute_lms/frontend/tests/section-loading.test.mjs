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
