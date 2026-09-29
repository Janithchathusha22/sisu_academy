import test from 'node:test'
import assert from 'node:assert/strict'
import {providerSocials} from '../src/commerce/socials.js'

test('social icons are exclusive to provider profiles',()=>{
  const links={facebook:'https://www.facebook.com/example'}
  for(const role of ['Teacher','Institute']) assert.deepEqual(providerSocials(role,links),links)
  assert.deepEqual(providerSocials('Student',links),{})
})
test('social links omit malformed, unsafe and unsupported values',()=>{
  assert.deepEqual(providerSocials('Teacher',{facebook:'javascript:alert(1)',youtube:'https://user:secret@example.com',instagram:'http://example.com',unknown:'https://example.com'}),{})
  assert.deepEqual(providerSocials('Institute','invalid JSON'),{})
  assert.deepEqual(providerSocials('Institute','{"linkedin":"https://linkedin.com/in/example"}'),{linkedin:'https://linkedin.com/in/example'})
})
