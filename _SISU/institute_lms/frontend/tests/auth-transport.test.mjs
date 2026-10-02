import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'

test('API transport obtains the current Supabase session and sends its bearer token', async()=>{
  const source=await readFile(new URL('../src/lib/api.js',import.meta.url),'utf8')
  assert.match(source,/authClient\(\)\.auth\.getSession\(\)/)
  assert.match(source,/Authorization:\s*`Bearer \$\{token\}`/)
  assert.match(source,/api\('\/api\/me'\)/)
})

test('browser Supabase configuration contains only public VITE variables',async()=>{
  const source=await readFile(new URL('../src/lib/supabase.js',import.meta.url),'utf8')
  assert.match(source,/VITE_SUPABASE_(PUBLISHABLE|ANON)_KEY/)
  assert.doesNotMatch(source,/SERVICE_ROLE|SECRET_KEY/)
})
