import test from 'node:test'
import assert from 'node:assert/strict'
import { canAccess, billing, graphemes, safeLink } from '../src/rules.js'
const enrollment={active:1,fee:6000,access_override:'Automatic'}
test('first installment required even before due date',()=>assert.equal(canAccess(enrollment,[{status:'Unpaid',due_date:'2027-01-01'}],'2026-09-23').allowed,false))
test('paid first installment opens until next deadline',()=>assert.equal(canAccess(enrollment,[{status:'Paid',due_date:'2026-09-01'},{status:'Unpaid',due_date:'2026-10-01'}],'2026-09-23').allowed,true))
test('deadline closes access even before overdue cron runs',()=>assert.equal(canAccess(enrollment,[{status:'Paid',due_date:'2026-09-01'},{status:'Unpaid',due_date:'2026-09-23'}],'2026-09-23').allowed,false))
test('manual close wins over grace and settled payments',()=>assert.equal(canAccess({...enrollment,access_override:'Closed',grace_until:'2027-01-01'},[{status:'Paid',due_date:'2026-09-01'}],'2026-09-23').allowed,false))
test('inactive membership cannot use manual open',()=>assert.equal(canAccess({...enrollment,active:0,access_override:'Open'},[]).allowed,false))
test('billing boundary and extra students',()=>{assert.equal(billing(499,15000),15000);assert.equal(billing(500,15000),15000);assert.equal(billing(501,15000),15050);assert.equal(billing(528,15000),16400)})
test('visible character counting supports combined Unicode',()=>{assert.equal(graphemes('a\u0301'),1);assert.equal(graphemes('👩‍🏫'),1);assert.ok(graphemes('පුංචි පියවර') < 'පුංචි පියවර'.length)})
test('unsafe CTA protocols are rejected',()=>{assert.equal(safeLink('javascript:alert(1)'),null);assert.equal(safeLink('http://example.com'),null);assert.equal(safeLink('https://example.com'),'https://example.com')})
