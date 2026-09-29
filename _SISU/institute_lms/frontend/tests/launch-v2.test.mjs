import test from 'node:test'
import assert from 'node:assert/strict'
import {quotePlan,defaultConfig,effectiveFeature} from '../src/launch/config.js'
import {calendarFile,dueTasks,toolActive} from '../src/study/tools.js'
import {videoBackgrounds} from '../src/study/backgrounds.js'
test('V2 ranges include 100 free and move to paid at 101; explicit regional table wins',()=>{
 assert.equal(quotePlan(100,'D').amount,0);assert.equal(quotePlan(101,'D').amount,49)
 assert.equal(quotePlan(250,'A').amount,20);assert.equal(quotePlan(251,'E').amount,119)
 assert.equal(quotePlan(5000,'D').amount,499);assert.equal(quotePlan(5001).amount,null)
 assert.throws(()=>quotePlan(-1));assert.throws(()=>quotePlan(1.5));assert.throws(()=>quotePlan(1,'Z'))
})
test('feature precedence respects locks, future starts and exact expiry fallback',()=>{
 const c=defaultConfig();c.planDefaults.games=true;c.countryOverrides.games=false;c.features.games={value:true,from:'2026-01-01T00:00:00Z',until:'2026-02-01T00:00:00Z'}
 assert.equal(effectiveFeature('games',c,Date.parse('2025-12-31')).value,false)
 assert.equal(effectiveFeature('games',c,Date.parse('2026-01-02')).source,'Tenant contract')
 assert.equal(effectiveFeature('games',c,Date.parse('2026-02-01')).source,'Country override')
 c.locks.games=true;assert.equal(effectiveFeature('games',c).value,false)
 c.features.ai={value:true};assert.equal(effectiveFeature('ai',c).value,false)
 assert.equal(effectiveFeature('unknown',c).value,false)
})
test('student tool expiry is exact and calendar export escapes injected event fields',()=>{
 const state={entitlements:{todo:100},todos:[{id:'one',title:'Math\nEND:VEVENT, next;',due:'2026-09-25',archived:false},{id:'two',due:'2026-09-25',archived:true}]}
 assert.equal(toolActive(state,'todo',99),true);assert.equal(toolActive(state,'todo',100),false)
 assert.equal(dueTasks(state,'2026-09-25').length,1)
 const ics=calendarFile(state.todos);assert.equal(ics.split('\r\nBEGIN:VEVENT').length,2);assert.ok(ics.includes('Math\\nEND:VEVENT\\, next\\;'))
})
test('only unique HTTPS backgrounds from the supplied media host are registered',()=>{
 assert.equal(videoBackgrounds.length,16);assert.equal(new Set(videoBackgrounds.map(v=>v.src)).size,16)
 for(const v of videoBackgrounds){const u=new URL(v.src);assert.equal(u.origin,'https://d8j0ntlcm91z4.cloudfront.net');assert.ok(u.pathname.endsWith('.mp4'))}
})
